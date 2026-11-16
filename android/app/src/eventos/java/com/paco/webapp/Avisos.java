package com.paco.webapp;

import android.Manifest;
import android.app.Activity;
import android.app.AlarmManager;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.job.JobInfo;
import android.app.job.JobScheduler;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.TimeZone;

/** Avisos 30 min antes de cada servicio con F&B, leídos del calendario eventos.ics de la web. */
public class Avisos {
    static final String ICS = "https://franciscocampillopacheco-oss.github.io/eventos-palau/eventos/eventos.ics";
    static final String CANAL = "avisos";
    static final long ANTES = 30 * 60 * 1000L;
    static final long HORIZONTE = 4L * 24 * 60 * 60 * 1000L;

    public static void iniciar(Activity a) {
        crearCanal(a);
        if (Build.VERSION.SDK_INT >= 33 &&
            a.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            a.requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);
        }
        programarJob(a);
        actualizarEnHilo(a);
    }

    static void crearCanal(Context c) {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CANAL, "Avisos de servicios", NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("30 minutos antes de cada servicio con F&B");
            c.getSystemService(NotificationManager.class).createNotificationChannel(ch);
        }
    }

    static void programarJob(Context c) {
        try {
            JobScheduler js = (JobScheduler) c.getSystemService(Context.JOB_SCHEDULER_SERVICE);
            JobInfo ji = new JobInfo.Builder(7001, new ComponentName(c, AvisosJob.class))
                .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
                .setPeriodic(60 * 60 * 1000L)
                .setPersisted(true)
                .build();
            js.schedule(ji);
        } catch (Exception e) { }
    }

    public static void actualizarEnHilo(Context c) {
        final Context app = c.getApplicationContext();
        new Thread(() -> {
            try { actualizar(app); } catch (Exception e) { reprogramarGuardado(app); }
        }).start();
    }

    static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences("avisos", Context.MODE_PRIVATE);
    }

    static synchronized void actualizar(Context c) throws Exception {
        HttpURLConnection con = (HttpURLConnection) new URL(ICS + "?t=" + System.currentTimeMillis()).openConnection();
        con.setConnectTimeout(15000);
        con.setReadTimeout(20000);
        con.setUseCaches(false);
        try (InputStream in = con.getInputStream()) {
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] b = new byte[8192];
            int n;
            while ((n = in.read(b)) > 0) bo.write(b, 0, n);
            String ics = bo.toString("UTF-8");
            if (!ics.contains("BEGIN:VCALENDAR")) throw new Exception("ics no válido");
            prefs(c).edit().putString("ics", ics).apply();
            programar(c, ics);
        } finally {
            con.disconnect();
        }
    }

    static void reprogramarGuardado(Context c) {
        String ics = prefs(c).getString("ics", null);
        if (ics != null) programar(c, ics);
    }

    static String limpiar(String v) {
        return v.replace("\\n", " · ").replace("\\,", ",").replace("\;", ";").replace("\\\\", "\\");
    }

    static synchronized void programar(Context c, String ics) {
        AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
        SharedPreferences p = prefs(c);
        for (String id : p.getStringSet("ids", new HashSet<>())) {
            try {
                PendingIntent viejo = PendingIntent.getBroadcast(c, Integer.parseInt(id),
                    new Intent(c, AvisoReceiver.class), PendingIntent.FLAG_NO_CREATE | PendingIntent.FLAG_IMMUTABLE);
                if (viejo != null) { am.cancel(viejo); viejo.cancel(); }
            } catch (Exception e) { }
        }
        String[] lineas = ics.replace("\r\n ", "").replace("\n ", "").split("\r?\n");
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd'T'HHmmss", Locale.ROOT);
        f.setTimeZone(TimeZone.getTimeZone("Europe/Madrid"));
        SimpleDateFormat hm = new SimpleDateFormat("HH:mm", new Locale("es", "ES"));
        hm.setTimeZone(TimeZone.getTimeZone("Europe/Madrid"));
        long ahora = System.currentTimeMillis();
        Set<String> ids = new HashSet<>();
        String uid = null, sum = null, loc = null; Date ini = null; boolean dentro = false;
        for (String l : lineas) {
            if (l.equals("BEGIN:VEVENT")) { dentro = true; uid = sum = loc = null; ini = null; continue; }
            if (!dentro) continue;
            if (l.startsWith("UID:")) uid = l.substring(4);
            else if (l.startsWith("SUMMARY:")) sum = limpiar(l.substring(8));
            else if (l.startsWith("LOCATION:")) loc = limpiar(l.substring(9));
            else if (l.startsWith("DTSTART")) {
                try { ini = f.parse(l.substring(l.indexOf(':') + 1).trim()); } catch (Exception e) { ini = null; }
            } else if (l.equals("END:VEVENT")) {
                dentro = false;
                if (ini == null || sum == null) continue;
                long t = ini.getTime() - ANTES;
                if (t <= ahora || t > ahora + HORIZONTE) continue;
                int rc = (uid != null ? uid : sum + ini.getTime()).hashCode();
                Intent i = new Intent(c, AvisoReceiver.class)
                    .putExtra("titulo", "En 30 min: " + sum)
                    .putExtra("texto", hm.format(ini) + (loc != null && !loc.isEmpty() ? " · " + loc : ""))
                    .putExtra("id", rc);
                PendingIntent pi = PendingIntent.getBroadcast(c, rc, i,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
                try {
                    if (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms())
                        am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, t, pi);
                    else
                        am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, t, pi);
                } catch (SecurityException e) {
                    am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, t, pi);
                }
                ids.add(String.valueOf(rc));
            }
        }
        p.edit().putStringSet("ids", ids).apply();
    }
}
