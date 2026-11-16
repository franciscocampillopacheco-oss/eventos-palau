package com.paco.webapp;

import android.app.job.JobParameters;
import android.app.job.JobService;

/** Cada hora relee el calendario de eventos y reprograma los avisos. */
public class AvisosJob extends JobService {
    @Override
    public boolean onStartJob(JobParameters params) {
        final android.content.Context app = getApplicationContext();
        new Thread(() -> {
            boolean otra = false;
            try { Avisos.actualizar(app); } catch (Exception e) { otra = true; }
            jobFinished(params, otra);
        }).start();
        return true;
    }

    @Override
    public boolean onStopJob(JobParameters params) { return true; }
}
