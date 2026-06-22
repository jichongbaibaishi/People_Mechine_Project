package com.example.stressassessment;

import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;
import java.util.HashMap;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {
    private WebView webView;
    private TextToSpeech tts;
    private boolean ttsReady = false;
    private int currentUtteranceIndex = -1;
    private int totalUtterances = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webview);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setAllowFileAccess(true);
        webSettings.setAllowContentAccess(true);
        webSettings.setLoadWithOverviewMode(true);
        webSettings.setUseWideViewPort(true);
        webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);
        webSettings.setMediaPlaybackRequiresUserGesture(false);
        webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());

        webView.addJavascriptInterface(new TTSInterface(), "AndroidTTS");

        tts = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) {
                int result = tts.setLanguage(Locale.CHINESE);
                if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    tts.setLanguage(Locale.CHINA);
                }
                tts.setPitch(1.2f);
                tts.setSpeechRate(0.85f);
                ttsReady = true;

                tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                    @Override
                    public void onStart(String utteranceId) {
                        currentUtteranceIndex = Integer.parseInt(utteranceId);
                        runOnUiThread(() -> webView.evaluateJavascript(
                            "if(window.onTTSStart) window.onTTSStart(" + currentUtteranceIndex + ");", null));
                    }

                    @Override
                    public void onDone(String utteranceId) {
                        int idx = Integer.parseInt(utteranceId);
                        currentUtteranceIndex = idx;
                        if (idx >= totalUtterances - 1) {
                            // 全部播放完毕
                            runOnUiThread(() -> webView.evaluateJavascript(
                                "if(window.onTTSDone) window.onTTSDone();", null));
                        } else {
                            // 下一句开始
                            runOnUiThread(() -> webView.evaluateJavascript(
                                "if(window.onTTSNext) window.onTTSNext(" + (idx + 1) + ");", null));
                        }
                    }

                    @Override
                    public void onError(String utteranceId) {
                        runOnUiThread(() -> webView.evaluateJavascript(
                            "if(window.onTTSError) window.onTTSError();", null));
                    }
                });
            }
        });

        webView.loadUrl("file:///android_asset/www/launcher.html");
    }

    private class TTSInterface {
        @JavascriptInterface
        public void speak(String text) {
            if (ttsReady && tts != null) {
                tts.stop();
                HashMap<String, String> params = new HashMap<>();
                params.put(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, "0");
                tts.speak(text, TextToSpeech.QUEUE_FLUSH, params);
            }
        }

        // 逐句播放，startIndex 为从第几句开始（0-based）
        @JavascriptInterface
        public void speakSentences(String jsonSentences, int startIndex) {
            if (ttsReady && tts != null) {
                tts.stop();
                currentUtteranceIndex = startIndex;
                // 解析 JSON 数组
                String[] sentences = parseJsonArray(jsonSentences);
                totalUtterances = sentences.length;
                for (int i = startIndex; i < sentences.length; i++) {
                    HashMap<String, String> params = new HashMap<>();
                    params.put(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, String.valueOf(i));
                    int queueMode = (i == startIndex) ? TextToSpeech.QUEUE_FLUSH : TextToSpeech.QUEUE_ADD;
                    tts.speak(sentences[i], queueMode, params);
                }
            }
        }

        @JavascriptInterface
        public void stop() {
            if (tts != null) {
                tts.stop();
            }
        }

        @JavascriptInterface
        public boolean isReady() {
            return ttsReady;
        }

        @JavascriptInterface
        public void setPitch(float pitch) {
            if (tts != null) tts.setPitch(pitch);
        }

        @JavascriptInterface
        public void setRate(float rate) {
            if (tts != null) tts.setSpeechRate(rate);
        }

        @JavascriptInterface
        public int getCurrentIndex() {
            return currentUtteranceIndex;
        }

        @JavascriptInterface
        public int getTotalCount() {
            return totalUtterances;
        }
    }

    // 简单解析 JSON 字符串数组: ["s1","s2","s3"]
    private String[] parseJsonArray(String json) {
        json = json.trim();
        if (json.startsWith("[")) json = json.substring(1);
        if (json.endsWith("]")) json = json.substring(0, json.length() - 1);
        java.util.List<String> list = new java.util.ArrayList<>();
        StringBuilder sb = new StringBuilder();
        boolean inQuote = false;
        for (int i = 0; i < json.length(); i++) {
            char c = json.charAt(i);
            if (c == '"' && (i == 0 || json.charAt(i - 1) != '\\')) {
                inQuote = !inQuote;
            } else if (c == ',' && !inQuote) {
                String s = sb.toString().trim();
                if (!s.isEmpty()) list.add(s);
                sb = new StringBuilder();
            } else if (inQuote) {
                sb.append(c);
            }
        }
        String last = sb.toString().trim();
        if (!last.isEmpty()) list.add(last);
        return list.toArray(new String[0]);
    }

    @Override
    protected void onDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
