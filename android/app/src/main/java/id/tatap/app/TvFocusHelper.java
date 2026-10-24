package id.tatap.app;

import android.app.AlertDialog;
import android.app.UiModeManager;
import android.content.Context;
import android.content.DialogInterface;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.drawable.Drawable;
import android.text.style.ImageSpan;
import android.view.View;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.ListView;

import com.google.android.material.button.MaterialButton;
import com.google.android.material.card.MaterialCardView;

public class TvFocusHelper {
    private static final int COLOR_FOCUSED_STROKE = Color.parseColor("#0A84FF");
    private static final int COLOR_NORMAL_STROKE = Color.parseColor("#2C2C34");

    public static boolean isTv(Context context) {
        if (context == null) return false;
        if (context.getPackageName().endsWith(".tv")) {
            return true;
        }
        UiModeManager uiModeManager = (UiModeManager) context.getSystemService(Context.UI_MODE_SERVICE);
        if (uiModeManager != null && uiModeManager.getCurrentModeType() == Configuration.UI_MODE_TYPE_TELEVISION) {
            return true;
        }
        PackageManager pm = context.getPackageManager();
        if (pm.hasSystemFeature("android.software.leanback")) {
            return true;
        }
        // Fallback: perangkat tanpa layar sentuh adalah Android TV box / stick
        return !pm.hasSystemFeature(PackageManager.FEATURE_TOUCHSCREEN);
    }

    public static void attachFocusScale(final View view, final float targetScale, final float elevationDp) {
        if (view == null) return;
        view.setFocusable(true);
        view.setFocusableInTouchMode(false); // Di TV, remote fokus tidak membutuhkan touch mode

        final float density = view.getResources().getDisplayMetrics().density;
        final float elevationPx = elevationDp * density;

        view.setOnFocusChangeListener((v, hasFocus) -> {
            float scale = hasFocus ? targetScale : 1.0f;
            v.animate().cancel();
            v.animate()
                    .scaleX(scale)
                    .scaleY(scale)
                    .setDuration(80)
                    .withLayer()
                    .setInterpolator(new android.view.animation.DecelerateInterpolator())
                    .start();

            if (elevationPx > 0 && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                v.setElevation(hasFocus ? elevationPx : 0f);
                v.setTranslationZ(hasFocus ? elevationPx / 2f : 0f);
            }

            // Sorot border secara dinamis tanpa mengubah strokeWidth (mencegah requestLayout & outline thrashing)
            if (v instanceof MaterialCardView) {
                MaterialCardView card = (MaterialCardView) v;
                card.setStrokeColor(hasFocus ? COLOR_FOCUSED_STROKE : COLOR_NORMAL_STROKE);
            } else if (v instanceof MaterialButton) {
                MaterialButton btn = (MaterialButton) v;
                btn.setStrokeColor(ColorStateList.valueOf(hasFocus ? COLOR_FOCUSED_STROKE : Color.parseColor("#33FFFFFF")));
                btn.setBackgroundTintList(ColorStateList.valueOf(hasFocus ? Color.parseColor("#1E2B45") : Color.parseColor("#CC161B26")));
            } else if (v instanceof ImageButton
                    || (v != null && (v.getId() == androidx.media3.ui.R.id.exo_rew
                    || v.getId() == androidx.media3.ui.R.id.exo_rew_with_amount
                    || v.getId() == androidx.media3.ui.R.id.exo_ffwd
                    || v.getId() == androidx.media3.ui.R.id.exo_ffwd_with_amount))) {
                if (v.getId() == androidx.media3.ui.R.id.exo_play_pause
                        || v.getId() == androidx.media3.ui.R.id.exo_play
                        || v.getId() == androidx.media3.ui.R.id.exo_pause) {
                    v.setBackgroundResource(R.drawable.bg_exo_play_center);
                } else {
                    v.setBackgroundResource(R.drawable.bg_exo_icon_btn);
                }
            } else if (v.getBackground() instanceof GradientDrawable) {
                GradientDrawable gd = (GradientDrawable) v.getBackground().mutate();
                if (hasFocus) {
                    gd.setStroke((int) (2f * density), COLOR_FOCUSED_STROKE);
                } else {
                    gd.setStroke((int) (1f * density), Color.parseColor("#2B3448"));
                }
            }
        });
    }

    public static void attachCardFocus(final MaterialCardView card) {
        attachFocusScale(card, 1.04f, 0f);
    }

    /**
     * Menerapkan fokus otomatis kursor remote D-Pad pada AlertDialog di Android TV (10-Foot UI).
     * Memastikan ListView dialog atau tombol aksi utama langsung mendapatkan fokus,
     * mencegah kursor D-Pad tersangkut di view latar belakang player.
     */
    public static AlertDialog applyDialogTvFocus(AlertDialog dialog) {
        if (dialog == null) return null;
        Context context = dialog.getContext();
        if (!isTv(context)) return dialog;

        Runnable focusAction = () -> {
            ListView lv = dialog.getListView();
            if (lv != null) {
                lv.setFocusable(true);
                lv.setFocusableInTouchMode(false);
                lv.requestFocus();
                if (lv.getAdapter() != null && lv.getAdapter().getCount() > 0) {
                    lv.setSelection(0);
                }
            } else {
                Button btn = dialog.getButton(DialogInterface.BUTTON_POSITIVE);
                if (btn != null && btn.getVisibility() == View.VISIBLE) {
                    btn.setFocusable(true);
                    btn.requestFocus();
                } else {
                    Button btnNeg = dialog.getButton(DialogInterface.BUTTON_NEGATIVE);
                    if (btnNeg != null && btnNeg.getVisibility() == View.VISIBLE) {
                        btnNeg.setFocusable(true);
                        btnNeg.requestFocus();
                    }
                }
            }
        };

        if (dialog.isShowing()) {
            android.view.Window w = dialog.getWindow();
            if (w != null && w.getDecorView() != null) {
                w.getDecorView().post(focusAction);
            } else {
                focusAction.run();
            }
        } else {
            dialog.setOnShowListener(di -> focusAction.run());
        }
        return dialog;
    }

    /**
     * ImageSpan yang memusatkan posisi vertikal ikon secara matematis
     * terhadap tinggi font (ascent & descent) untuk tampilan 10-Foot UI Android TV.
     */
    public static class CenteredImageSpan extends ImageSpan {
        public CenteredImageSpan(Drawable drawable) {
            super(drawable);
        }

        @Override
        public void draw(Canvas canvas, CharSequence text, int start, int end,
                         float x, int top, int y, int bottom, Paint paint) {
            Drawable b = getDrawable();
            if (b == null) return;
            canvas.save();
            Paint.FontMetricsInt fm = paint.getFontMetricsInt();
            int transY = (y + fm.descent + y + fm.ascent) / 2 - b.getBounds().height() / 2;
            canvas.translate(x, transY);
            b.draw(canvas);
            canvas.restore();
        }
    }
}
