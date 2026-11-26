package com.paco.webapp;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Al encender el móvil o actualizar la app, vuelve a programar los avisos. */
public class ArranqueReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent in) {
        Avisos.crearCanal(c);
        Avisos.reprogramarGuardado(c);
        Avisos.programarJob(c);
        Avisos.actualizarEnHilo(c);
    }
}
