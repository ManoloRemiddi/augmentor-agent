// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
//! Augmentor's private parent/child protocol. No listener, tray or login item.
use crate::managers::{
    audio::AudioRecordingManager, model::ModelManager, transcription::TranscriptionManager,
};
use crate::{commands, settings, shortcut, utils};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::io::{BufRead, Read, Write};
use std::sync::{
    atomic::{AtomicBool, AtomicU8, Ordering},
    Arc, Mutex,
};
use tauri::{AppHandle, Emitter, Listener, Manager};

pub fn external_shortcut() -> bool {
    active() && std::env::var("AUGMENTOR_HANDY_EXTERNAL_SHORTCUT").as_deref() == Ok("1")
}

pub fn active() -> bool {
    std::env::var("AUGMENTOR_HANDY_EMBEDDED").as_deref() == Ok("1")
}

#[derive(Clone, Serialize, Deserialize, specta::Type)]
#[serde(deny_unknown_fields)]
pub struct Theme {
    pub background: String,
    pub foreground: String,
    pub accent: String,
    pub border: String,
    pub opacity: f64,
    pub animated: bool,
    pub mode: String,
}
impl Default for Theme {
    fn default() -> Self {
        Self {
            background: "#132327".into(),
            foreground: "#edf3f3".into(),
            accent: "#a8dfce".into(),
            border: "#48746b".into(),
            opacity: 0.85,
            animated: true,
            mode: "dark".into(),
        }
    }
}
impl Theme {
    fn validate(&self) -> Result<(), String> {
        for c in [
            &self.background,
            &self.foreground,
            &self.accent,
            &self.border,
        ] {
            if c.len() != 7
                || !c.starts_with('#')
                || !c.as_bytes()[1..].iter().all(u8::is_ascii_hexdigit)
            {
                return Err("Invalid overlay colour".into());
            }
        }
        if !self.opacity.is_finite()
            || !(0.35..=1.0).contains(&self.opacity)
            || !["light", "dark"].contains(&self.mode.as_str())
        {
            return Err("Invalid overlay theme".into());
        }
        Ok(())
    }
}
pub struct Embedded {
    enabled: AtomicBool,
    holder: AtomicU8,
    theme: Mutex<Theme>,
    revision: Mutex<u64>,
    phase: Mutex<String>,
    problem: Mutex<Option<String>>,
    conversation: Mutex<Option<String>>,
}
impl Embedded {
    fn new() -> Self {
        Self {
            enabled: AtomicBool::new(false),
            holder: AtomicU8::new(0),
            theme: Mutex::new(Theme::default()),
            revision: Mutex::new(0),
            phase: Mutex::new("disabled".into()),
            problem: Mutex::new(None),
            conversation: Mutex::new(None),
        }
    }
}
struct Editing<'a>(&'a AtomicU8);
impl Drop for Editing<'_> {
    fn drop(&mut self) {
        self.0
            .compare_exchange(3, 0, Ordering::SeqCst, Ordering::SeqCst)
            .ok();
    }
}
fn edit(state: &Embedded) -> Result<Editing<'_>, String> {
    state
        .holder
        .compare_exchange(0, 3, Ordering::SeqCst, Ordering::SeqCst)
        .map_err(|_| "Microphone is busy")?;
    Ok(Editing(&state.holder))
}

#[tauri::command]
#[specta::specta]
pub fn overlay_theme(app: AppHandle) -> Option<Theme> {
    app.try_state::<Embedded>()
        .and_then(|s| s.theme.lock().ok().map(|v| v.clone()))
}

/// Called by both shortcut backends before the coordinator accepts an event.
pub fn admit(app: &AppHandle, pressed: bool) -> bool {
    let Some(s) = app.try_state::<Embedded>() else {
        return !active();
    };
    if !s.enabled.load(Ordering::SeqCst) {
        return false;
    }
    if pressed {
        match s
            .holder
            .compare_exchange(0, 1, Ordering::SeqCst, Ordering::SeqCst)
        {
            Ok(_) | Err(1) => true,
            _ => false,
        }
    } else {
        s.holder.load(Ordering::SeqCst) == 1
    }
}

pub fn configure(app: &AppHandle) {
    let mut s = settings::get_settings(app);
    // Installation/startup/update authority remains in Augmentor.
    s.show_tray_icon = false;
    s.start_hidden = true;
    s.autostart_enabled = false;
    s.update_checks_enabled = false;
    s.debug_mode = false;
    s.log_level = settings::LogLevel::Warn;
    s.always_on_microphone = false;
    s.auto_submit = false;
    s.post_process_enabled = false;
    settings::write_settings(app, s);
}

fn public_settings(app: &AppHandle) -> Value {
    let s = settings::get_settings(app);
    json!({"shortcut": s.bindings.get("transcribe").map(|v| &v.current_binding), "activation": s.shortcut_activation,
        "model": s.selected_model, "language": s.selected_language, "translate": s.translate_to_english,
        "microphone": s.selected_microphone, "paste_method": s.paste_method, "typing_tool": s.typing_tool,
        "clipboard": s.clipboard_handling, "history_limit": s.history_limit, "retention": s.recording_retention_period})
}

fn enable(app: &AppHandle, enabled: bool) -> Result<(), String> {
    let state = app.state::<Embedded>();
    if !enabled {
        state.enabled.store(false, Ordering::SeqCst);
        utils::cancel_current_operation(app);
        shortcut::suspend_all_shortcuts(app);
        app.state::<Arc<AudioRecordingManager>>()
            .stop_microphone_stream();
        app.state::<Arc<TranscriptionManager>>()
            .unload_model()
            .map_err(|e| e.to_string())?;
        state
            .holder
            .compare_exchange(1, 0, Ordering::SeqCst, Ordering::SeqCst)
            .ok();
        *state.phase.lock().map_err(|_| "State unavailable")? = "disabled".into();
        return Ok(());
    }
    if state.enabled.load(Ordering::SeqCst) {
        return Ok(());
    }
    commands::initialize_enigo(app.clone())?;
    let s = settings::get_settings(app);
    // Initialize backend state, then explicitly verify registration: upstream
    // init logs registration failures but does not return them to its caller.
    if !external_shortcut() {
        commands::initialize_shortcuts(app.clone())?;
        shortcut::suspend_all_shortcuts(app);
    }
    let binding = s
        .bindings
        .get("transcribe")
        .ok_or("Missing dictation shortcut")?
        .clone();
    if !external_shortcut() {
        shortcut::register_shortcut(app, binding)?;
    }
    state.enabled.store(true, Ordering::SeqCst);
    *state.problem.lock().map_err(|_| "State unavailable")? = None;
    *state.phase.lock().map_err(|_| "State unavailable")? = "ready".into();
    Ok(())
}

async fn dispatch(app: &AppHandle, request: &Value) -> Result<Value, String> {
    let state = app.state::<Embedded>();
    let method = request
        .get("method")
        .and_then(Value::as_str)
        .ok_or("Missing method")?;
    let p = request.get("params").cloned().unwrap_or_else(|| json!({}));
    let text = |key: &str| -> Result<String, String> {
        p.get(key)
            .and_then(Value::as_str)
            .filter(|v| v.len() <= 1024)
            .map(str::to_owned)
            .ok_or_else(|| format!("Invalid {key}"))
    };
    match method {
        "status" => {
            let s = settings::get_settings(app);
            let mm = app.state::<Arc<ModelManager>>();
            let available = mm
                .get_model_info(&s.selected_model)
                .is_some_and(|v| v.is_downloaded);
            let phase = state.phase.lock().map_err(|_| "State unavailable")?.clone();
            Ok(
                json!({"protocol":"augmentor-handy/1", "enabled":state.enabled.load(Ordering::SeqCst),
                "phase": if state.enabled.load(Ordering::SeqCst) && !available {"setup-needed"} else {phase.as_str()},
                "revision":*state.revision.lock().map_err(|_| "State unavailable")?, "settings":public_settings(app),
                "theme":state.theme.lock().map_err(|_| "State unavailable")?.clone(),
                "error":state.problem.lock().map_err(|_| "State unavailable")?.clone(), "tray":false}),
            )
        }
        "enable" => {
            enable(
                app,
                p.get("enabled")
                    .and_then(Value::as_bool)
                    .ok_or("Invalid enabled")?,
            )?;
            Ok(json!({}))
        }
        "theme" => {
            let theme: Theme = serde_json::from_value(p).map_err(|_| "Invalid theme")?;
            theme.validate()?;
            *state.theme.lock().map_err(|_| "State unavailable")? = theme.clone();
            app.emit("augmentor-theme", theme)
                .map_err(|e| e.to_string())?;
            Ok(json!({}))
        }
        "settings" => {
            let _guard = edit(&state)?;
            if state.holder.load(Ordering::SeqCst) == 1 {
                return Err("Finish dictation before changing its settings".into());
            }
            let mut revision = state.revision.lock().map_err(|_| "State unavailable")?;
            if p.get("revision").and_then(Value::as_u64) != Some(*revision) {
                return Err("Dictation settings changed; refresh before saving".into());
            }
            let changes = p
                .get("values")
                .and_then(Value::as_object)
                .ok_or("Invalid settings")?;
            let mut s = settings::get_settings(app);
            for (key, value) in changes {
                match key.as_str() {
                    "shortcut" => {}
                    "activation" => {
                        s.shortcut_activation = serde_json::from_value(value.clone())
                            .map_err(|_| "Invalid activation")?
                    }
                    "language" => {
                        let lang = value.as_str().ok_or("Invalid language")?;
                        if lang.len() > 16
                            || !lang.chars().all(|c| c.is_ascii_alphanumeric() || c == '-')
                        {
                            return Err("Invalid language".into());
                        }
                        s.selected_language = lang.into();
                    }
                    "translate" => {
                        s.translate_to_english = value.as_bool().ok_or("Invalid translation")?
                    }
                    "microphone" => {
                        s.selected_microphone = serde_json::from_value(value.clone())
                            .map_err(|_| "Invalid microphone")?
                    }
                    "paste_method" => {
                        s.paste_method = serde_json::from_value(value.clone())
                            .map_err(|_| "Invalid paste method")?
                    }
                    "typing_tool" => {
                        s.typing_tool = serde_json::from_value(value.clone())
                            .map_err(|_| "Invalid typing tool")?
                    }
                    "clipboard" => {
                        s.clipboard_handling = serde_json::from_value(value.clone())
                            .map_err(|_| "Invalid clipboard mode")?
                    }
                    "history_limit" => {
                        let n = value
                            .as_u64()
                            .filter(|n| *n <= 100)
                            .ok_or("Invalid history limit")?;
                        s.history_limit = n as usize;
                    }
                    "retention" => {
                        s.recording_retention_period = serde_json::from_value(value.clone())
                            .map_err(|_| "Invalid retention")?
                    }
                    _ => return Err(format!("Unsupported setting: {key}")),
                }
            }
            if let Some(v) = changes.get("shortcut") {
                let key = v
                    .as_str()
                    .filter(|v| v.len() <= 128)
                    .ok_or("Invalid shortcut")?;
                if !state.enabled.load(Ordering::SeqCst) || external_shortcut() {
                    shortcut::validate_shortcut_for_implementation(key, s.keyboard_implementation)?;
                    s.bindings
                        .get_mut("transcribe")
                        .ok_or("Missing shortcut")?
                        .current_binding = key.into();
                } else {
                    let result =
                        shortcut::change_binding(app.clone(), "transcribe".into(), key.into())?;
                    if !result.success {
                        return Err(result
                            .error
                            .unwrap_or_else(|| "Shortcut registration failed".into()));
                    }
                    s.bindings = settings::get_settings(app).bindings;
                }
            }
            settings::write_settings(app, s);
            if !state.enabled.load(Ordering::SeqCst) {
                shortcut::suspend_all_shortcuts(app);
            }
            if changes.contains_key("microphone") {
                app.state::<Arc<AudioRecordingManager>>()
                    .update_selected_device()
                    .map_err(|e| e.to_string())?;
            }
            *revision += 1;
            Ok(json!({"revision":*revision}))
        }
        "models" => {
            let mm = app.state::<Arc<ModelManager>>();
            Ok(json!(mm.get_available_models().iter().map(|m| json!({"id":m.id,"name":m.name,"size_mb":m.size_mb,"installed":m.is_downloaded,"downloading":m.is_downloading,"partial_size":m.partial_size,"languages":m.supported_languages,"translation":m.supports_translation,"source":m.source})).collect::<Vec<_>>()))
        }
        "model.select" => {
            let _guard = edit(&state)?;
            commands::models::switch_active_model(app, &text("id")?)?;
            if !state.enabled.load(Ordering::SeqCst) {
                app.state::<Arc<TranscriptionManager>>()
                    .unload_model()
                    .map_err(|e| e.to_string())?;
            }
            *state.revision.lock().map_err(|_| "State unavailable")? += 1;
            Ok(json!({}))
        }
        "model.download" => {
            let id = text("id")?;
            let mm = app.state::<Arc<ModelManager>>().inner().clone();
            if mm.get_model_info(&id).is_none() {
                return Err("Unknown model".into());
            }
            let handle = app.clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = mm.download_model(&id).await {
                    if let Some(s) = handle.try_state::<Embedded>() {
                        if let Ok(mut p) = s.problem.lock() {
                            *p = Some(e.to_string());
                        }
                    }
                }
            });
            Ok(json!({"accepted":true}))
        }
        "model.cancel" => {
            app.state::<Arc<ModelManager>>()
                .cancel_download(&text("id")?)
                .map_err(|e| e.to_string())?;
            Ok(json!({}))
        }
        "shortcut.event" => {
            if !external_shortcut() {
                return Err("External shortcuts are not active".into());
            }
            let pressed = p
                .get("pressed")
                .and_then(Value::as_bool)
                .ok_or("Invalid shortcut event")?;
            let s = settings::get_settings(app);
            let binding = s.bindings.get("transcribe").ok_or("Missing shortcut")?;
            shortcut::embedded_event(app, &binding.current_binding, pressed);
            Ok(json!({}))
        }
        "devices" => Ok(json!(commands::audio::get_available_microphones().await?)),
        "cancel" => {
            utils::cancel_current_operation(app);
            Ok(json!({}))
        }
        "conversation.acquire" => {
            let token = text("token")?;
            if let Some(expires) = p.get("expires_at").and_then(Value::as_u64) {
                let now = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map_err(|_| "System clock unavailable")?
                    .as_nanos();
                if now >= u128::from(expires) {
                    return Err("Voice input request expired; start voice again.".into());
                }
            }
            let mut owner = state.conversation.lock().map_err(|_| "State unavailable")?;
            if owner.as_ref() != Some(&token) {
                state
                    .holder
                    .compare_exchange(0, 2, Ordering::SeqCst, Ordering::SeqCst)
                    .map_err(|_| "Microphone is busy")?;
                *owner = Some(token);
            }
            Ok(json!({}))
        }
        "conversation.release" => {
            let token = text("token")?;
            let mut owner = state.conversation.lock().map_err(|_| "State unavailable")?;
            if owner.as_ref() == Some(&token) {
                *owner = None;
                state
                    .holder
                    .compare_exchange(2, 0, Ordering::SeqCst, Ordering::SeqCst)
                    .ok();
            }
            Ok(json!({}))
        }
        "quit" => {
            state.enabled.store(false, Ordering::SeqCst);
            utils::cancel_current_operation(app);
            app.exit(0);
            Ok(json!({}))
        }
        _ => Err("Unsupported dictation operation".into()),
    }
}

pub fn start(app: &AppHandle) {
    app.manage(Embedded::new());
    for name in [
        "show-overlay",
        "hide-overlay",
        "recording-error",
        "transcription-error",
        "paste-error",
    ] {
        let handle = app.clone();
        app.listen(name, move |event| {
            let s = handle.state::<Embedded>();
            if let Ok(mut phase) = s.phase.lock() {
                *phase = if name == "show-overlay" {
                    serde_json::from_str::<String>(event.payload())
                        .unwrap_or_else(|_| "recording".into())
                } else if s.enabled.load(Ordering::SeqCst) {
                    "ready".into()
                } else {
                    "disabled".into()
                };
            }
            if name.ends_with("error") {
                let payload = serde_json::from_str::<Value>(event.payload()).unwrap_or(Value::Null);
                let message = if name == "paste-error" {
                    "Could not insert transcription. Check clipboard and input permissions.".to_string()
                } else {
                    payload.as_str().or_else(|| payload.get("detail").and_then(Value::as_str))
                        .unwrap_or("Voice input failed. Check microphone permissions and the selected model.").to_string()
                };
                if let Ok(mut problem) = s.problem.lock() { *problem = Some(message); }
            } else if name == "show-overlay" && event.payload() == "\"recording\"" {
                if let Ok(mut problem) = s.problem.lock() { *problem = None; }
            }
            if name != "show-overlay" {
                s.holder
                    .compare_exchange(1, 0, Ordering::SeqCst, Ordering::SeqCst)
                    .ok();
            }
        });
    }
    let handle = app.clone();
    std::thread::spawn(move || {
        let mut input = std::io::stdin().lock();
        loop {
            let mut line = String::new();
            let count = input.by_ref().take(65537).read_line(&mut line);
            if !matches!(count, Ok(n) if n > 0) || line.len() > 65536 {
                break;
            }
            let Ok(request) = serde_json::from_str::<Value>(&line) else {
                continue;
            };
            let app = handle.clone();
            tauri::async_runtime::spawn(async move {
                let id = request.get("id").cloned().unwrap_or(Value::Null);
                let response = match dispatch(&app, &request).await {
                    Ok(value) => json!({"id":id,"result":value}),
                    Err(error) => json!({"id":id,"error":error}),
                };
                let mut out = std::io::stdout().lock();
                let _ = writeln!(out, "{}", response);
                let _ = out.flush();
            });
        }
        // Parent loss must never leave capture or shortcuts running orphaned.
        utils::cancel_current_operation(&handle);
        handle.exit(0);
    });
}
