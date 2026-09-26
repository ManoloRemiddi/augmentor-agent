// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// A single registered shortcut, not a keyboard event tap. Parent owns lifetime.
import AppKit
import Carbon

func emit(_ value: [String: Any]) {
    if let data = try? JSONSerialization.data(withJSONObject: value) {
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data([10]))
    }
}

func resolveKey(_ text: String) -> [String: Any] {
    let special: [String: Int] = [
        "@F1": kVK_F1, "@F2": kVK_F2, "@F3": kVK_F3, "@F4": kVK_F4,
        "@F5": kVK_F5, "@F6": kVK_F6, "@F7": kVK_F7, "@F8": kVK_F8,
        "@F9": kVK_F9, "@F10": kVK_F10, "@F11": kVK_F11, "@F12": kVK_F12,
        "@F13": kVK_F13, "@F14": kVK_F14, "@F15": kVK_F15, "@F16": kVK_F16,
        "@F17": kVK_F17, "@F18": kVK_F18, "@F19": kVK_F19, "@F20": kVK_F20,
        "@Left": kVK_LeftArrow, "@Right": kVK_RightArrow,
        "@Up": kVK_UpArrow, "@Down": kVK_DownArrow,
        "@Home": kVK_Home, "@End": kVK_End, "@PageUp": kVK_PageUp,
        "@PageDown": kVK_PageDown, "@Escape": kVK_Escape, "@Tab": kVK_Tab,
        "@Return": kVK_Return, "@Backspace": kVK_Delete, "@Delete": kVK_ForwardDelete]
    if let code = special[text] { return ["keyCode": code] }
    // Resolve printable keys against the active Unicode keyboard layout. Do not
    // silently use ANSI key positions when the user selected a different layout.
    guard text.count == 1,
          let source = TISCopyCurrentKeyboardLayoutInputSource()?.takeRetainedValue(),
          let property = TISGetInputSourceProperty(source, kTISPropertyUnicodeKeyLayoutData) else {
        return ["error": "This input source has no supported Unicode keyboard layout."]
    }
    let data = Unmanaged<CFData>.fromOpaque(property).takeUnretainedValue()
    guard let bytes = CFDataGetBytePtr(data) else { return ["error": "Keyboard layout data is unavailable."] }
    let layout = UnsafeRawPointer(bytes).assumingMemoryBound(to: UCKeyboardLayout.self)
    for code in UInt16(0)...UInt16(127) {
        var dead: UInt32 = 0
        var count: Int = 0
        var characters = [UniChar](repeating: 0, count: 8)
        let status = UCKeyTranslate(layout, code, UInt16(kUCKeyActionDisplay), 0,
            UInt32(LMGetKbdType()), OptionBits(kUCKeyTranslateNoDeadKeysMask),
            &dead, characters.count, &count, &characters)
        if status == noErr && String(utf16CodeUnits: characters, count: count).lowercased() == text.lowercased() {
            return ["keyCode": code]
        }
    }
    return ["error": "That character has no unmodified key in the current keyboard layout."]
}

@main struct Hotkey {
    static func main() {
        let args = CommandLine.arguments
        if args.count == 3 && args[1] == "--resolve" {
            let result = resolveKey(args[2]); emit(result)
            exit(result["error"] == nil ? 0 : 2)
        }
        let allowed = UInt32(cmdKey | shiftKey | optionKey | controlKey | kEventKeyModifierFnMask)
        guard args.count == 3, let key = UInt32(args[1]), key <= 127,
              let modifiers = UInt32(args[2]), modifiers != 0,
              modifiers & ~allowed == 0 else {
            emit(["error": "Supply a key code and Command, Control, Option, Shift or Fn modifiers."])
            exit(2)
        }
        let application = NSApplication.shared
        application.setActivationPolicy(.accessory)
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        var handler: EventHandlerRef?
        let installed = InstallEventHandler(GetApplicationEventTarget(), { _, event, _ in
            guard let event else { return OSStatus(eventNotHandledErr) }
            var identifier = EventHotKeyID()
            let status = GetEventParameter(event, EventParamName(kEventParamDirectObject),
                EventParamType(typeEventHotKeyID), nil, MemoryLayout<EventHotKeyID>.size,
                nil, &identifier)
            guard status == noErr, identifier.signature == 0x4155474D, identifier.id == 1 else {
                return OSStatus(eventNotHandledErr)
            }
            emit(["event": "pressed"])
            return noErr
        }, 1, &spec, nil, &handler)
        guard installed == noErr else {
            emit(["error": "Could not install the shortcut handler.", "status": installed]); exit(1)
        }
        var hotkey: EventHotKeyRef?
        let status = RegisterEventHotKey(key, modifiers,
            EventHotKeyID(signature: 0x4155474D, id: 1), GetApplicationEventTarget(), OptionBits(kEventHotKeyExclusive), &hotkey)
        guard status == noErr else {
            emit(["error": "macOS could not register that shortcut. Choose another combination.", "status": status]); exit(1)
        }
        emit(["event": "ready", "keyCode": key, "modifiers": modifiers])
        let layoutObserver = DistributedNotificationCenter.default().addObserver(
            forName: NSNotification.Name(rawValue: kTISNotifySelectedKeyboardInputSourceChanged as String),
            object: nil, queue: .main) { _ in emit(["event": "layoutChanged"]) }
        // EOF from the owner releases the registration without a global daemon.
        DispatchQueue.global().async {
            while !FileHandle.standardInput.readData(ofLength: 1024).isEmpty {}
            DispatchQueue.main.async {
                if let hotkey { UnregisterEventHotKey(hotkey) }
                application.terminate(nil)
            }
        }
        application.run()
        DistributedNotificationCenter.default().removeObserver(layoutObserver)
    }
}
