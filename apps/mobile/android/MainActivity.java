// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
package com.augmentor.remote;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.graphics.Color;
import android.net.Uri;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceError;
import android.webkit.WebSettings;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Thin internal Android host. All Augmentor screens and actions remain remote. */
public final class MainActivity extends Activity {
    private WebView web;
    private String origin;
    private boolean suspended;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        showConnection();
    }

    private void insets(View view) {
        view.setOnApplyWindowInsetsListener((v, value) -> {
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                // API 35+ edge-to-edge does not resize this container for the IME.
                // Include keyboard insets so WebView reports the usable viewport.
                android.graphics.Insets bars = value.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout() | WindowInsets.Type.ime());
                v.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            } else {
                v.setPadding(value.getSystemWindowInsetLeft(), value.getSystemWindowInsetTop(), value.getSystemWindowInsetRight(), value.getSystemWindowInsetBottom());
            }
            return value;
        });
    }

    private void showConnection() {
        if (web != null) { web.loadUrl("about:blank"); web.destroy(); web = null; }
        origin = null;
        LinearLayout outer = new LinearLayout(this);
        outer.setOrientation(LinearLayout.VERTICAL); outer.setBackgroundColor(Color.rgb(16,24,25));
        insets(outer);
        LinearLayout form = new LinearLayout(this);form.setOrientation(LinearLayout.VERTICAL);form.setPadding(24,24,24,24);
        TextView label = new TextView(this);label.setText("Connect to your Augmentor computer\nEnter its private HTTPS address. Tailscale must be connected.");label.setTextSize(18);
        EditText address = new EditText(this);address.setSingleLine(true);address.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        address.setHint("https://computer.tailnet.ts.net:8443");
        address.setText(getPreferences(MODE_PRIVATE).getString("origin", ""));
        address.setContentDescription("Computer HTTPS address");
        Button connect = new Button(this);connect.setText("Connect");
        TextView error = new TextView(this);
        form.addView(label);form.addView(address);form.addView(connect);form.addView(error);outer.addView(form);setContentView(outer);
        connect.setOnClickListener(v -> {
            String value = address.getText().toString().trim();
            Uri uri = Uri.parse(value);
            if (!"https".equals(uri.getScheme()) || uri.getHost() == null || uri.getUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null || !(uri.getPath() == null || uri.getPath().isEmpty() || "/".equals(uri.getPath()))) {
                error.setText("Enter an HTTPS address without a path, query or credentials."); return;
            }
            origin = "https://" + uri.getEncodedAuthority();
            getPreferences(MODE_PRIVATE).edit().putString("origin", origin).apply();
            openDesktop();
        });
    }

    private boolean sameOrigin(Uri uri) {
        return origin != null && origin.equals("https://" + uri.getEncodedAuthority()) && "https".equals(uri.getScheme());
    }

    private void openDesktop() {
        web = new WebView(this);web.setBackgroundColor(Color.rgb(16,24,25));
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);settings.setDomStorageEnabled(false);
        settings.setAllowFileAccess(false);settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        android.webkit.CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);
        // No JavaScript/native interface, file chooser, microphone or TLS bypass.
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !sameOrigin(request.getUrl());
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) new AlertDialog.Builder(MainActivity.this)
                    .setMessage("Cannot reach the computer. Check Tailscale and that Augmentor Remote is running.")
                    .setPositiveButton("Retry", (d,w) -> view.loadUrl(origin + "/"))
                    .setNegativeButton("Connection settings", (d,w) -> showConnection()).show();
            }
        });
        LinearLayout container = new LinearLayout(this);container.setBackgroundColor(Color.rgb(16,24,25));insets(container);
        container.addView(web, new LinearLayout.LayoutParams(-1,-1));setContentView(container);
        web.loadUrl(origin + "/");
    }

    @Override protected void onStop() {
        // Release single-viewer ownership in background. No agent/task cancellation.
        if (web != null) { suspended = true; web.loadUrl("about:blank"); web.onPause(); }
        super.onStop();
    }
    @Override protected void onStart() {
        super.onStart();
        if (web != null && suspended) { suspended=false;web.onResume();web.loadUrl(origin + "/"); }
    }
    @Override public void onBackPressed() {
        if (web == null) { super.onBackPressed(); return; }
        new AlertDialog.Builder(this).setMessage("Close the remote view? Your agent continues on the computer.")
            .setPositiveButton("Close view", (d,w) -> showConnection()).setNegativeButton("Keep open",null).show();
    }
    @Override protected void onDestroy() {
        if (web != null) { web.destroy();web=null; }
        super.onDestroy();
    }
}
