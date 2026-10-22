package id.tatap.app;

import android.app.Activity;
import android.content.Context;
import android.media.AudioManager;
import android.media.audiofx.HapticGenerator;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.view.GestureDetector;
import android.view.HapticFeedbackConstants;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.SharedPreferences;
import android.content.pm.ActivityInfo;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.util.TypedValue;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.LinearLayout;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import androidx.media3.common.C;
import androidx.media3.common.Format;
import androidx.media3.common.ForwardingPlayer;
import androidx.media3.common.MediaItem;
import androidx.media3.common.MimeTypes;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.PlaybackParameters;
import androidx.media3.common.Player;
import androidx.media3.datasource.DefaultHttpDataSource;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.exoplayer.analytics.AnalyticsListener;
import androidx.media3.exoplayer.DefaultLoadControl;
import androidx.media3.exoplayer.DefaultRenderersFactory;
import androidx.media3.exoplayer.upstream.DefaultBandwidthMeter;
import androidx.media3.common.audio.AudioProcessor;
import androidx.media3.exoplayer.audio.AudioSink;
import androidx.media3.exoplayer.audio.DefaultAudioSink;
import androidx.media3.exoplayer.audio.TeeAudioProcessor;
import androidx.media3.exoplayer.hls.HlsMediaSource;
import androidx.media3.ui.AspectRatioFrameLayout;
import androidx.media3.ui.PlayerView;
import androidx.media3.ui.SubtitleView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.ShortBuffer;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import android.content.Intent;
import android.widget.EditText;
import android.app.PictureInPictureParams;
import android.app.RemoteAction;
import android.app.PendingIntent;
import android.graphics.drawable.Icon;
import android.util.Rational;
import android.graphics.Rect;
import android.content.BroadcastReceiver;
import android.content.IntentFilter;
import android.content.pm.PackageManager;

public class PlayerActivity extends Activity {
    private ExoPlayer player;
    private ForwardingPlayer forwardingPlayer;
    private PlayerView playerView;
    private Button btnPip;
    private Button btnPortraitPip;
    private BroadcastReceiver pipReceiver;
    private static final String ACTION_PIP_CONTROL = "id.tatap.app.PIP_CONTROL";
    private static final String EXTRA_PIP_ACTION = "pip_action";
    private static final int PIP_ACTION_REWIND = 1;
    private static final int PIP_ACTION_PLAY_PAUSE = 2;
    private static final int PIP_ACTION_FORWARD = 3;
    private GestureDetector gestureDetector;
    private AudioManager audioManager;
    private View hudOsd;
    private TextView tvOsdIcon, tvOsdVal, tvRippleLeft, tvRippleRight;
    private ProgressBar pbOsdBar;
    private View hudHoldSpeed;
    private TextView tvHoldSpeedIcon, tvHoldSpeedText;
    private boolean isHoldingSpeed = false;
    private boolean isHoldingRewind = false;
    private float holdOriginalSpeed = 1.0f;
    private int holdRewindAccumMs = 0;
    private TextView tvPlayerTitle, tvSubStatus;
    private ImageButton btnPlayerBack;
    private View layoutTopBar;
    private View layoutBuffering;
    private TextView tvBufferingText;
    private TextView tvSubtitles;
    private final Handler handler = new Handler(Looper.getMainLooper());

    private String slug;
    private int ep;
    private String title;
    private List<Integer> episodeList = new ArrayList<>();
    private boolean isEpisodeListLoading = false;
    private View btnExoNext;
    private View btnExoPrev;
    private View btnExoSub;
    private View btnExoSettings;
    private View btnExoFullscreen;
    private Button btnAspect;
    private Button btnQuality;
    private Button btnSpeed;
    private Button btnSubStyle;
    private Button btnSubSelector;
    private Button btnSkipOpEd;
    private float currentPlaybackSpeed = 1.0f;
    private boolean isHapticEnabled = true;
    private boolean isGeneralHapticEnabled = true;
    private boolean isSceneHapticEnabled = false; // Haptic scene audio dimatikan
    private boolean isTimeBarListenerAttached = false;
    private volatile boolean isVideoPlaying = false;
    private volatile boolean isInOpEd = false;
    private Object hapticGenerator;
    private int currentAudioSessionId = C.AUDIO_SESSION_ID_UNSET;
    private int lastHapticBrightnessStep = -1;

    // Watch Portrait View components
    private View flPlayerWrapper;
    private View layoutPortraitBottom;
    private TextView tvPortraitAnimeTitle;
    private TextView tvPortraitCurrentEp;
    private TextView tvPortraitEpCount;
    private Button btnPortraitSub;
    private Button btnPortraitQuality;
    private Button btnPortraitSpeed;
    private Button btnPortraitFullscreen;
    private Button btnPortraitSort;
    private RecyclerView rvPortraitRanges;
    private RecyclerView rvPortraitEpisodes;
    private boolean isPortraitAscending = true;
    private PortraitEpisodeAdapter portraitEpisodeAdapter;
    private PortraitRangeAdapter portraitRangeAdapter;
    private PortraitEpisodeRange activePortraitRange = null;
    private final List<PortraitEpisodeRange> portraitRanges = new ArrayList<>();
    private android.window.OnBackInvokedCallback backInvokedCallback;

    public static class PortraitEpisodeRange {
        public final int start;
        public final int end;
        public final String label;

        public PortraitEpisodeRange(int start, int end) {
            this.start = start;
            this.end = end;
            this.label = start + " - " + end;
        }
    }

    private int dpToPx(int dp) {
        return (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, dp, getResources().getDisplayMetrics());
    }
    private static final float[] PLAYBACK_SPEEDS = new float[]{0.5f, 0.75f, 1.0f, 1.25f, 1.5f, 1.75f, 2.0f};
    private static final String[] PLAYBACK_SPEED_LABELS = new String[]{"0.5x", "0.75x", "1.0x (Normal)", "1.25x", "1.5x", "1.75x", "2.0x"};
    private long introStartMs = 0;
    private long introEndMs = 0;
    private long outroStartMs = 0;
    private long outroEndMs = 0;
    private long currentSkipTargetMs = 0;
    private boolean autoSkipOpEd = false;
    private boolean hasAutoSkippedIntro = false;
    private boolean hasAutoSkippedOutro = false;
    private float currentBrightness = 0.5f;
    private float currentVolumeFraction = -1f;
    private int activeGestureZone = 0; // 0 = none / deadzone, 1 = brightness (left edge), 2 = volume (right edge)
    private long pendingResumePosMs = -1;
    private boolean hasPromptedResume = false;
    private long lastProgressSaveMs = 0;
    private View btnScreenLock;
    private View btnScreenUnlock;
    private boolean isScreenLocked = false;
    private final Runnable hideUnlockButtonRunnable = () -> {
        if (btnScreenUnlock != null && isScreenLocked) {
            btnScreenUnlock.animate()
                    .alpha(0f)
                    .setDuration(250)
                    .withEndAction(() -> {
                        if (isScreenLocked && btnScreenUnlock != null) {
                            btnScreenUnlock.setVisibility(View.GONE);
                        }
                    })
                    .start();
        }
    };

    // Subtitle Engine State
    public static class SubtitleCue {
        public final long startMs;
        public final long endMs;
        public final String text;

        public SubtitleCue(long startMs, long endMs, String text) {
            this.startMs = startMs;
            this.endMs = endMs;
            this.text = text;
        }
    }

    private volatile List<SubtitleCue> currentCues = new ArrayList<>();
    private int currentSubLoadId = 0;

    private String rawStreamUrl = "";
    private String streamReferer = "";
    private String masterStreamUrl = "";
    private int currentResizeMode = AspectRatioFrameLayout.RESIZE_MODE_FIT;
    private final List<JSONObject> streamVariants = new ArrayList<>();
    private String activeQuality = "best";
    private List<JSONObject> subtitleTracks = new ArrayList<>();
    private String enSourceSubUrl = "";
    private String idNativeSubUrl = "";
    private String activeSubUrl = "";
    private String activeSubLang = "id"; // Default Indonesian
    private String activeEngine = "gtx"; // "gtx" | "gtx+" | "aigtx" | "ai" | "raw"
    private boolean subEnabled = true;
    private String activeStreamMode = "sub"; // "sub" | "dub"
    private String requestMode = "sub";
    private String customSubtitleName = "";
    private String customSubtitleUrl = "";
    private static final int REQUEST_CODE_PICK_SUBTITLE = 8769;
    private boolean hasAiKey = false;
    private String configuredAiModel = "gemini-2.0-flash";
    private boolean isHlsMode = false;
    private boolean hasFallbackAttempted = false;
    private boolean hasAutoRetriedStream = false;
    private int consecutiveRecoveryAttempts = 0;
    private static final int MAX_RECOVERY_ATTEMPTS = 2;
    private int currentResolveLoadId = 0;

    private boolean isHlsStream(String url) {
        if (url == null || url.isEmpty()) return false;
        String lower = url.toLowerCase();
        int qIdx = lower.indexOf('?');
        String path = (qIdx >= 0) ? lower.substring(0, qIdx) : lower;
        if (path.endsWith(".m3u8") || path.endsWith("/m3u8")) return true;
        if (path.endsWith(".ts") || path.endsWith(".ts.jpg") || path.endsWith(".jpg")
                || path.endsWith(".mp4") || path.endsWith(".m4s") || path.endsWith(".aac")) return false;
        return lower.contains(".m3u8")
                || lower.contains("format=m3u8")
                || lower.contains("output=m3u8")
                || lower.contains("/api/hls")
                || lower.contains("/hls/playlist");
    }

    private String lastSubtitleText = "";
    private boolean hasAppliedTrackSelectionForStream = false;
    private final Runnable subtitleSyncRunnable = new Runnable() {
        @Override
        public void run() {
            if (player != null && subEnabled) {
                long pos = player.getCurrentPosition();
                SubtitleCue active = findActiveCue(pos);
                if (active != null) {
                    if (tvSubtitles.getVisibility() != View.VISIBLE || !active.text.equals(lastSubtitleText)) {
                        lastSubtitleText = active.text;
                        tvSubtitles.setText(active.text);
                        tvSubtitles.setVisibility(View.VISIBLE);
                    }
                } else {
                    if (tvSubtitles.getVisibility() == View.VISIBLE) {
                        lastSubtitleText = "";
                        tvSubtitles.setText("");
                        tvSubtitles.setVisibility(View.GONE);
                    }
                }
            } else {
                if (tvSubtitles != null && tvSubtitles.getVisibility() == View.VISIBLE) {
                    lastSubtitleText = "";
                    tvSubtitles.setText("");
                    tvSubtitles.setVisibility(View.GONE);
                }
            }

            if (player != null) {
                checkSkipTimes(player.getCurrentPosition());
                recordWatchProgress(false);
            }

            if (player != null && player.isPlaying()) {
                int syncInterval = TvFocusHelper.isTv(PlayerActivity.this) ? 150 : 75;
                handler.postDelayed(this, syncInterval);
            }
        }
    };

    private void doSkipOpEd() {
        if (player != null && currentSkipTargetMs > 0) {
            long pos = player.getCurrentPosition();
            if (introEndMs > introStartMs && pos >= introStartMs && pos < introEndMs) {
                hasAutoSkippedIntro = true;
            }
            if (outroEndMs > outroStartMs && pos >= outroStartMs && pos < outroEndMs) {
                hasAutoSkippedOutro = true;
            }
            player.seekTo(currentSkipTargetMs);
            if (btnSkipOpEd != null) {
                if (TvFocusHelper.isTv(this) && (btnSkipOpEd.isFocused() || getCurrentFocus() == btnSkipOpEd)) {
                    if (playerView != null) {
                        playerView.requestFocus();
                    }
                }
                btnSkipOpEd.setVisibility(View.GONE);
            }
            long sec = currentSkipTargetMs / 1000;
            currentSkipTargetMs = 0;
            String timeStr = String.format("%02d:%02d", sec / 60, sec % 60);
            performHapticClick();
            Toast.makeText(this, "Melompat ke " + timeStr, Toast.LENGTH_SHORT).show();
        }
    }

    private void updateSkipButtonLabel(boolean isIntro) {
        if (btnSkipOpEd == null) return;
        boolean isTv = TvFocusHelper.isTv(this);
        String action = isIntro ? "Lewati Opening" : "Lewati Ending";
        if (isTv) {
            boolean focused = btnSkipOpEd.isFocused() || getCurrentFocus() == btnSkipOpEd;
            btnSkipOpEd.setText(focused ? (action + " [OK]") : ("[▼] " + action));
        } else {
            btnSkipOpEd.setText(action);
        }
    }

    private void checkSkipTimes(long posMs) {
        if (btnSkipOpEd == null || player == null) return;
        boolean inIntro = (introEndMs > introStartMs && introEndMs > 0 && (introEndMs - introStartMs) >= 5_000
                && posMs >= introStartMs && posMs < (introEndMs - 500));
        boolean inOutro = (outroEndMs > outroStartMs && outroEndMs > 0 && (outroEndMs - outroStartMs) >= 5_000
                && posMs >= outroStartMs && posMs < (outroEndMs - 500));
        isInOpEd = (inIntro || inOutro);

        if (autoSkipOpEd) {
            if (inIntro && !hasAutoSkippedIntro) {
                hasAutoSkippedIntro = true;
                currentSkipTargetMs = introEndMs + 500;
                doSkipOpEd();
                return;
            } else if (inOutro && !hasAutoSkippedOutro) {
                hasAutoSkippedOutro = true;
                currentSkipTargetMs = outroEndMs + 500;
                doSkipOpEd();
                return;
            }
        }

        boolean isTv = TvFocusHelper.isTv(this);
        if (inIntro) {
            currentSkipTargetMs = introEndMs + 500;
            updateSkipButtonLabel(true);
            if (btnSkipOpEd.getVisibility() != View.VISIBLE) {
                btnSkipOpEd.setVisibility(View.VISIBLE);
                if (isTv) {
                    btnSkipOpEd.requestFocus();
                    updateSkipButtonLabel(true);
                }
            }
        } else if (inOutro) {
            currentSkipTargetMs = outroEndMs + 500;
            updateSkipButtonLabel(false);
            if (btnSkipOpEd.getVisibility() != View.VISIBLE) {
                btnSkipOpEd.setVisibility(View.VISIBLE);
                if (isTv) {
                    btnSkipOpEd.requestFocus();
                    updateSkipButtonLabel(false);
                }
            }
        } else {
            currentSkipTargetMs = 0;
            if (btnSkipOpEd.getVisibility() == View.VISIBLE) {
                if (isTv && (btnSkipOpEd.isFocused() || getCurrentFocus() == btnSkipOpEd)) {
                    if (playerView != null) {
                        playerView.requestFocus();
                    }
                }
                btnSkipOpEd.setVisibility(View.GONE);
            }
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        boolean isTvOrLandscape = TvFocusHelper.isTv(this) || getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
        if (isTvOrLandscape) {
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
        } else {
            getWindow().clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
        }
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            backInvokedCallback = this::handleBackAction;
            try {
                getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT,
                    backInvokedCallback
                );
            } catch (Throwable ignored) {}
        }

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                WindowManager.LayoutParams lp = getWindow().getAttributes();
                if (lp != null) {
                    lp.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
                    getWindow().setAttributes(lp);
                }
            }
        } catch (Throwable ignored) {}

        if (TvFocusHelper.isTv(this)) {
            setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
        }

        setContentView(R.layout.activity_player);

        slug = getIntent().getStringExtra("slug");
        String passedMode = getIntent().getStringExtra("mode");
        requestMode = (passedMode != null && !passedMode.isEmpty() && "dub".equalsIgnoreCase(passedMode)) ? "dub" : "sub";
        ep = getIntent().getIntExtra("ep", 1);
        title = getIntent().getStringExtra("title");
        ArrayList<Integer> passedList = getIntent().getIntegerArrayListExtra("episode_list");
        if (passedList != null) {
            episodeList.addAll(passedList);
        }

        flPlayerWrapper = findViewById(R.id.fl_player_wrapper);
        layoutPortraitBottom = findViewById(R.id.layout_portrait_bottom);
        tvPortraitAnimeTitle = findViewById(R.id.tv_portrait_anime_title);
        tvPortraitCurrentEp = findViewById(R.id.tv_portrait_current_ep);
        tvPortraitEpCount = findViewById(R.id.tv_portrait_ep_count);
        btnPortraitSub = findViewById(R.id.btn_portrait_sub);
        btnPortraitQuality = findViewById(R.id.btn_portrait_quality);
        btnPortraitSpeed = findViewById(R.id.btn_portrait_speed);
        btnPortraitFullscreen = findViewById(R.id.btn_portrait_fullscreen);
        btnPortraitPip = findViewById(R.id.btn_portrait_pip);
        btnPortraitSort = findViewById(R.id.btn_portrait_sort);
        rvPortraitRanges = findViewById(R.id.rv_portrait_ranges);
        rvPortraitEpisodes = findViewById(R.id.rv_portrait_episodes);

        if (layoutPortraitBottom != null && !TvFocusHelper.isTv(this)) {
            if (title != null && !title.isEmpty()) {
                tvPortraitAnimeTitle.setText(title);
            } else {
                tvPortraitAnimeTitle.setText("Episode " + ep);
            }
            tvPortraitCurrentEp.setText("Memutar Episode " + ep);

            android.widget.ImageButton btnPortraitBack = findViewById(R.id.btn_portrait_back);
            if (btnPortraitBack != null) {
                btnPortraitBack.setOnClickListener(v -> handleBackAction());
            }

            if (btnPortraitPip != null) {
                if (isPipSupported()) {
                    btnPortraitPip.setVisibility(View.VISIBLE);
                    btnPortraitPip.setOnClickListener(v -> {
                        HapticHelper.performClick(v);
                        enterPipMode();
                    });
                } else {
                    btnPortraitPip.setVisibility(View.GONE);
                }
            }

            if (btnPortraitSub != null) {
                btnPortraitSub.setOnClickListener(v -> {
                    HapticHelper.performClick(v);
                    showSubtitleSelectorDialog();
                });
            }
            if (btnPortraitQuality != null) {
                btnPortraitQuality.setOnClickListener(v -> {
                    HapticHelper.performClick(v);
                    showQualitySelectorDialog();
                });
            }
            if (btnPortraitSpeed != null) {
                btnPortraitSpeed.setOnClickListener(v -> {
                    HapticHelper.performClick(v);
                    showSpeedSelectorDialog();
                });
            }
            if (btnPortraitFullscreen != null) {
                btnPortraitFullscreen.setOnClickListener(v -> {
                    HapticHelper.performClick(v);
                    setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
                });
            }
            if (btnPortraitSort != null) {
                btnPortraitSort.setOnClickListener(v -> {
                    HapticHelper.performClick(v);
                    isPortraitAscending = !isPortraitAscending;
                    btnPortraitSort.setText(isPortraitAscending ? "Urutan: 1 - N" : "Urutan: N - 1");
                    updatePortraitEpisodeDisplay();
                });
            }

            if (rvPortraitEpisodes != null) {
                rvPortraitEpisodes.setLayoutManager(new GridLayoutManager(this, 4));
                portraitEpisodeAdapter = new PortraitEpisodeAdapter();
                rvPortraitEpisodes.setAdapter(portraitEpisodeAdapter);
            }

            if (rvPortraitRanges != null) {
                rvPortraitRanges.setLayoutManager(new LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false));
                portraitRangeAdapter = new PortraitRangeAdapter();
                rvPortraitRanges.setAdapter(portraitRangeAdapter);
            }
        }

        ensureEpisodeListLoaded();

        playerView = findViewById(R.id.player_view);
        hudOsd = findViewById(R.id.hud_osd);
        tvOsdIcon = findViewById(R.id.tv_osd_icon);
        tvOsdVal = findViewById(R.id.tv_osd_val);
        pbOsdBar = findViewById(R.id.pb_osd_bar);
        tvRippleLeft = findViewById(R.id.tv_ripple_left);
        tvRippleRight = findViewById(R.id.tv_ripple_right);
        hudHoldSpeed = findViewById(R.id.hud_hold_speed);
        tvHoldSpeedIcon = findViewById(R.id.tv_hold_speed_icon);
        tvHoldSpeedText = findViewById(R.id.tv_hold_speed_text);

        layoutTopBar = findViewById(R.id.layout_top_bar);
        boolean isLandscape = TvFocusHelper.isTv(this) || getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
        if (layoutTopBar != null) {
            layoutTopBar.setVisibility(isLandscape ? View.VISIBLE : View.GONE);
        }
        tvPlayerTitle = findViewById(R.id.tv_player_title);
        tvSubStatus = findViewById(R.id.tv_sub_status);
        btnPlayerBack = findViewById(R.id.btn_player_back);

        layoutBuffering = findViewById(R.id.layout_buffering);
        tvBufferingText = findViewById(R.id.tv_buffering_text);
        tvSubtitles = findViewById(R.id.tv_subtitles);

        if (title != null && !title.isEmpty()) {
            tvPlayerTitle.setText(title + " - Ep " + ep);
        } else {
            tvPlayerTitle.setText("Episode " + ep);
        }

        if (btnPlayerBack != null) {
            btnPlayerBack.setOnClickListener(v -> handleBackAction());
        }

        btnPip = findViewById(R.id.btn_pip);
        if (btnPip != null) {
            if (isPipSupported()) {
                btnPip.setVisibility(View.VISIBLE);
                btnPip.setOnClickListener(v -> {
                    HapticHelper.performClick(v);
                    enterPipMode();
                });
            } else {
                btnPip.setVisibility(View.GONE);
            }
        }

        btnAspect = findViewById(R.id.btn_aspect);
        if (btnAspect != null) {
            btnAspect.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                cycleAspectRatio();
            });
        }

        btnQuality = findViewById(R.id.btn_quality);
        if (btnQuality != null) {
            btnQuality.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                showQualitySelectorDialog();
            });
        }

        btnSpeed = findViewById(R.id.btn_speed);
        if (btnSpeed != null) {
            btnSpeed.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                showSpeedSelectorDialog();
            });
        }
        currentPlaybackSpeed = 1.0f;
        updateSpeedButtonLabel();

        btnSubStyle = findViewById(R.id.btn_sub_style);
        if (btnSubStyle != null) {
            btnSubStyle.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                showSubtitleStyleDialog();
            });
        }

        btnSubSelector = findViewById(R.id.btn_sub_selector);
        if (btnSubSelector != null) {
            btnSubSelector.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                showSubtitleSelectorDialog();
            });
        }

        btnSkipOpEd = findViewById(R.id.btn_skip_op_ed);
        if (btnSkipOpEd != null) {
            btnSkipOpEd.setOnClickListener(v -> doSkipOpEd());
            if (TvFocusHelper.isTv(this)) {
                TvFocusHelper.attachFocusScale(btnSkipOpEd, 1.10f, 6f);
                btnSkipOpEd.setOnFocusChangeListener((v, hasFocus) -> {
                    boolean inIntro = (introEndMs > introStartMs && player != null
                            && player.getCurrentPosition() >= introStartMs && player.getCurrentPosition() < introEndMs);
                    updateSkipButtonLabel(inIntro);
                });
            }
        }

        btnScreenLock = findViewById(R.id.btn_screen_lock);
        if (btnScreenLock != null) {
            btnScreenLock.setOnClickListener(v -> lockScreen());
            if (TvFocusHelper.isTv(this)) {
                btnScreenLock.setVisibility(View.GONE);
            }
        }

        btnScreenUnlock = findViewById(R.id.btn_screen_unlock);
        if (btnScreenUnlock != null) {
            btnScreenUnlock.setOnClickListener(v -> unlockScreen());
            btnScreenUnlock.setVisibility(View.GONE);
        }

        try {
            SharedPreferences sp = getSharedPreferences("tatap_player_prefs", MODE_PRIVATE);
            autoSkipOpEd = sp.getBoolean("auto_skip_op_ed", false);
            isGeneralHapticEnabled = !TvFocusHelper.isTv(this) && sp.getBoolean("pref_general_haptic", sp.getBoolean("pref_haptic", true));
            isHapticEnabled = isGeneralHapticEnabled;
            isSceneHapticEnabled = !TvFocusHelper.isTv(this) && sp.getBoolean("pref_scene_haptic", false);
            currentResizeMode = TvFocusHelper.isTv(this)
                    ? AspectRatioFrameLayout.RESIZE_MODE_FIT
                    : sp.getInt("aspect_mode", AspectRatioFrameLayout.RESIZE_MODE_FIT);
            activeEngine = sp.getString("pref_sub_engine", "gtx");
            if ("aigtx".equals(activeEngine)) activeEngine = "gtx+";
            activeSubLang = sp.getString("pref_sub_lang", "id");
            subEnabled = sp.getBoolean("pref_sub_enabled", true);
            if (playerView != null) {
                playerView.setResizeMode(currentResizeMode);
                playerView.setHapticFeedbackEnabled(true);
            }
            updateAspectButtonLabel();
        } catch (Throwable ignored) {}

        updateLayoutForOrientation(getResources().getConfiguration().orientation);

        // Pastikan hideSystemUi / showSystemUi dieksekusi setelah decorView terpasang di window
        try {
            getWindow().getDecorView().post(this::applySystemUiVisibility);
        } catch (Throwable ignored) {}

        applySubtitleStyle();

        // Pasang respon fokus D-Pad TV pada tombol kontrol player
        TvFocusHelper.attachFocusScale(btnPlayerBack, 1.15f, 6f);
        TvFocusHelper.attachFocusScale(btnAspect, 1.08f, 6f);
        TvFocusHelper.attachFocusScale(btnQuality, 1.08f, 6f);
        TvFocusHelper.attachFocusScale(btnSpeed, 1.08f, 6f);
        TvFocusHelper.attachFocusScale(btnSubStyle, 1.08f, 6f);
        TvFocusHelper.attachFocusScale(btnSubSelector, 1.08f, 6f);

        try {
            audioManager = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        } catch (Throwable ignored) {}

        checkAiConfig();
        initExoPlayer();
        setupExoNativeControls();
        setupGestureControls();
        registerPipReceiver();
        checkAndPromptResume();
        resolveAndPlayStream();
    }

    private void cycleAspectRatio() {
        try {
            if (playerView == null) return;
            if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_FIT) {
                currentResizeMode = AspectRatioFrameLayout.RESIZE_MODE_ZOOM;
                Toast.makeText(this, "Mode Layar: ZOOM (Penuh)", Toast.LENGTH_SHORT).show();
            } else if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_ZOOM) {
                currentResizeMode = AspectRatioFrameLayout.RESIZE_MODE_FILL;
                Toast.makeText(this, "Mode Layar: FILL (Stretch)", Toast.LENGTH_SHORT).show();
            } else {
                currentResizeMode = AspectRatioFrameLayout.RESIZE_MODE_FIT;
                Toast.makeText(this, "Mode Layar: FIT (Skala Asli)", Toast.LENGTH_SHORT).show();
            }
            playerView.setResizeMode(currentResizeMode);
            getSharedPreferences("tatap_player_prefs", MODE_PRIVATE)
                    .edit().putInt("aspect_mode", currentResizeMode).apply();
            updateAspectButtonLabel();
        } catch (Throwable ignored) {}
    }

    private void updateAspectButtonLabel() {
        try {
            if (btnAspect == null) return;
            if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_ZOOM) {
                btnAspect.setText("Zoom");
            } else if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_FILL) {
                btnAspect.setText("Fill");
            } else {
                btnAspect.setText("Fit");
            }
        } catch (Throwable ignored) {}
    }

    private void hideSystemUi() {
        try {
            Window window = getWindow();
            if (window != null) {
                window.addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    android.view.WindowInsetsController controller = window.getInsetsController();
                    if (controller != null) {
                        controller.hide(android.view.WindowInsets.Type.statusBars() | android.view.WindowInsets.Type.navigationBars());
                        controller.setSystemBarsBehavior(android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
                    }
                } else {
                    View decorView = window.getDecorView();
                    if (decorView != null) {
                        decorView.setSystemUiVisibility(
                            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_FULLSCREEN
                        );
                    }
                }
            }
        } catch (Throwable ignored) {}
    }

    private void showSystemUiForPortrait() {
        try {
            Window window = getWindow();
            if (window != null) {
                window.clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    android.view.WindowInsetsController controller = window.getInsetsController();
                    if (controller != null) {
                        controller.show(android.view.WindowInsets.Type.statusBars() | android.view.WindowInsets.Type.navigationBars());
                        controller.setSystemBarsBehavior(android.view.WindowInsetsController.BEHAVIOR_DEFAULT);
                    }
                } else {
                    View decorView = window.getDecorView();
                    if (decorView != null) {
                        decorView.setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE);
                    }
                }
            }
        } catch (Throwable ignored) {}
    }

    private void applySystemUiVisibility() {
        if (TvFocusHelper.isTv(this) || getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE) {
            hideSystemUi();
        } else {
            showSystemUiForPortrait();
        }
    }

    private void updateLayoutForOrientation(int orientation) {
        boolean isTv = TvFocusHelper.isTv(this);
        if (isTv || orientation == Configuration.ORIENTATION_LANDSCAPE) {
            // Mode Landscape Fullscreen
            if (layoutPortraitBottom != null) {
                layoutPortraitBottom.setVisibility(View.GONE);
            }
            if (flPlayerWrapper != null) {
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
                flPlayerWrapper.setLayoutParams(lp);
            }
            // Pulihkan tombol aksi kontrol di landscape & TV
            if (btnAspect != null) btnAspect.setVisibility(View.VISIBLE);
            if (btnQuality != null) btnQuality.setVisibility(View.VISIBLE);
            if (btnSpeed != null) btnSpeed.setVisibility(View.VISIBLE);
            if (btnSubStyle != null) btnSubStyle.setVisibility(View.VISIBLE);
            if (btnSubSelector != null) btnSubSelector.setVisibility(View.VISIBLE);
            if (tvSubStatus != null) tvSubStatus.setVisibility(View.VISIBLE);
            if (layoutTopBar != null) {
                int padStart = isTv ? getResources().getDimensionPixelSize(R.dimen.tv_overscan_horizontal) : dpToPx(16);
                layoutTopBar.setPadding(padStart, dpToPx(16), padStart, dpToPx(16));
            }
            hideSystemUi();
        } else {
            // Mode Watch Portrait View
            if (layoutPortraitBottom != null) {
                layoutPortraitBottom.setVisibility(View.VISIBLE);
            }
            if (flPlayerWrapper != null) {
                int screenWidth = getResources().getDisplayMetrics().widthPixels;
                int playerHeight = (int) (screenWidth * 9f / 16f);
                if (playerHeight <= 0) playerHeight = dpToPx(215);
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT, playerHeight);
                flPlayerWrapper.setLayoutParams(lp);
            }
            // Sembunyikan 5 tombol berjejal di header saat portrait (fungsi sudah ada di panel bawah)
            if (btnAspect != null) btnAspect.setVisibility(View.GONE);
            if (btnQuality != null) btnQuality.setVisibility(View.GONE);
            if (btnSpeed != null) btnSpeed.setVisibility(View.GONE);
            if (btnSubStyle != null) btnSubStyle.setVisibility(View.GONE);
            if (btnSubSelector != null) btnSubSelector.setVisibility(View.GONE);
            if (tvSubStatus != null) tvSubStatus.setVisibility(View.GONE);
            if (btnScreenLock != null) btnScreenLock.setVisibility(View.GONE);
            if (layoutTopBar != null) {
                layoutTopBar.setVisibility(View.GONE);
                layoutTopBar.setPadding(dpToPx(12), dpToPx(8), dpToPx(12), dpToPx(8));
            }
            showSystemUiForPortrait();
            updatePortraitEpisodeDisplay();
        }
    }

    @Override
    public void onConfigurationChanged(@NonNull Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        updateLayoutForOrientation(newConfig.orientation);
    }

    private void exitLandscapeFullscreen() {
        if (!TvFocusHelper.isTv(this)) {
            setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
            handler.postDelayed(() -> {
                if (!isFinishing() && !isDestroyed()) {
                    setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_USER);
                }
            }, 500);
        }
    }

    private void handleBackAction() {
        performHapticTick();
        if (isScreenLocked) {
            showUnlockButtonBriefly();
            Toast.makeText(this, "Layar terkunci. Buka kunci layar terlebih dahulu.", Toast.LENGTH_SHORT).show();
            return;
        }
        if (!TvFocusHelper.isTv(this) && getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE) {
            exitLandscapeFullscreen();
            return;
        }
        finish();
    }

    @Override
    public void onBackPressed() {
        handleBackAction();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            try {
                applySystemUiVisibility();
            } catch (Throwable ignored) {}
        }
    }

    private void checkAiConfig() {
        new Thread(() -> {
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/settings").openConnection();
                conn.setConnectTimeout(2500);
                BufferedReader r = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = r.readLine()) != null) sb.append(line);
                r.close();
                JSONObject res = new JSONObject(sb.toString());
                JSONObject d = res.optJSONObject("data");
                if (d == null) d = res;
                String k = d.optString("translate_apikey", "");
                String m = d.optString("translate_model", "gemini-2.0-flash");
                hasAiKey = !k.isEmpty();
                if (!m.isEmpty()) configuredAiModel = m;
            } catch (Exception ignored) {}
        }).start();
    }

    private void initExoPlayer() {
        DefaultLoadControl loadControl = new DefaultLoadControl.Builder()
                .setBufferDurationsMs(
                        25_000, // minBufferMs (25s - mencegah starvation di 1080p)
                        50_000, // maxBufferMs (50s)
                        2_000,  // bufferForPlaybackMs (2s cepat mulai)
                        4_000   // bufferForPlaybackAfterRebufferMs (4s)
                )
                .setPrioritizeTimeOverSizeThresholds(false)
                .build();

        // Bandwidth meter dengan estimasi awal tinggi (25 Mbps) agar ExoPlayer langsung
        // memilih track video beresolusi optimal (1080p/720p) saat pertama kali memutar,
        // mencegah hardware decoder Android TV terlanjur mengunci buffer di 360p yang menyebabkan video ter-crop/zoom.
        DefaultBandwidthMeter bandwidthMeter = new DefaultBandwidthMeter.Builder(this)
                .setInitialBitrateEstimate(25_000_000)
                .build();

        DefaultRenderersFactory renderersFactory = new DefaultRenderersFactory(this) {
            @Override
            protected AudioSink buildAudioSink(Context context, boolean enableFloatOutput, boolean enableAudioTrackPlaybackParams) {
                if (TvFocusHelper.isTv(PlayerActivity.this) || !isSceneHapticEnabled) {
                    return super.buildAudioSink(context, enableFloatOutput, enableAudioTrackPlaybackParams);
                }
                return new DefaultAudioSink.Builder(context)
                        .setAudioProcessors(new AudioProcessor[] {
                            new TeeAudioProcessor(new SceneHapticAudioSink())
                        })
                        .build();
            }
        };
        renderersFactory.setExtensionRendererMode(DefaultRenderersFactory.EXTENSION_RENDERER_MODE_OFF)
                .setEnableDecoderFallback(true)
                .forceEnableMediaCodecAsynchronousQueueing();

        player = new ExoPlayer.Builder(this, renderersFactory)
                .setLoadControl(loadControl)
                .setBandwidthMeter(bandwidthMeter)
                .setSeekForwardIncrementMs(5000)
                .setSeekBackIncrementMs(5000)
                .build();

        player.addAnalyticsListener(new AnalyticsListener() {
            @Override
            public void onAudioSessionIdChanged(EventTime eventTime, int audioSessionId) {
                currentAudioSessionId = audioSessionId;
                setupHapticGenerator(audioSessionId);
            }
        });

        player.setVideoScalingMode(C.VIDEO_SCALING_MODE_SCALE_TO_FIT);

        forwardingPlayer = new ForwardingPlayer(player) {
            private boolean isNextAllowed() {
                boolean isTv = TvFocusHelper.isTv(PlayerActivity.this);
                boolean isPaused = (player != null && !player.isPlaying());
                return hasNextEpisode() && (!isTv || isPaused);
            }

            private boolean isPrevAllowed() {
                boolean isTv = TvFocusHelper.isTv(PlayerActivity.this);
                boolean isPaused = (player != null && !player.isPlaying());
                return hasPrevEpisode() && (!isTv || isPaused);
            }

            @Override
            public boolean isCommandAvailable(int command) {
                if (command == COMMAND_SEEK_TO_NEXT || command == COMMAND_SEEK_TO_NEXT_MEDIA_ITEM) {
                    return isNextAllowed();
                }
                if (command == COMMAND_SEEK_TO_PREVIOUS || command == COMMAND_SEEK_TO_PREVIOUS_MEDIA_ITEM) {
                    return isPrevAllowed();
                }
                return super.isCommandAvailable(command);
            }

            @Override
            public Commands getAvailableCommands() {
                Commands.Builder builder = super.getAvailableCommands().buildUpon();
                if (isNextAllowed()) {
                    builder.add(COMMAND_SEEK_TO_NEXT);
                    builder.add(COMMAND_SEEK_TO_NEXT_MEDIA_ITEM);
                } else {
                    builder.remove(COMMAND_SEEK_TO_NEXT);
                    builder.remove(COMMAND_SEEK_TO_NEXT_MEDIA_ITEM);
                }
                if (isPrevAllowed()) {
                    builder.add(COMMAND_SEEK_TO_PREVIOUS);
                    builder.add(COMMAND_SEEK_TO_PREVIOUS_MEDIA_ITEM);
                } else {
                    builder.remove(COMMAND_SEEK_TO_PREVIOUS);
                    builder.remove(COMMAND_SEEK_TO_PREVIOUS_MEDIA_ITEM);
                }
                return builder.build();
            }

            @Override
            public boolean hasNextMediaItem() {
                return isNextAllowed();
            }

            @Override
            public boolean hasPreviousMediaItem() {
                return isPrevAllowed();
            }

            @Override
            public void seekToNext() {
                if (hasNextEpisode()) {
                    playNextEpisode();
                }
            }

            @Override
            public void seekToNextMediaItem() {
                if (hasNextEpisode()) {
                    playNextEpisode();
                }
            }

            @Override
            public void seekToPrevious() {
                if (hasPrevEpisode()) {
                    playPrevEpisode();
                }
            }

            @Override
            public void seekToPreviousMediaItem() {
                if (hasPrevEpisode()) {
                    playPrevEpisode();
                }
            }
        };
        playerView.setPlayer(forwardingPlayer);
        playerView.setShowNextButton(true);
        playerView.setShowPreviousButton(true);

        // Hide default ExoPlayer subtitle view since we use seamless custom overlay
        SubtitleView subView = playerView.getSubtitleView();
        if (subView != null) {
            subView.setVisibility(View.GONE);
        }

        player.addListener(new Player.Listener() {
            @Override
            public void onTracksChanged(androidx.media3.common.Tracks tracks) {
                // Saat manifest/tracks HLS baru selesai di-resolve pertama kali oleh ExoPlayer,
                // kunci track selection HANYA SEKALI agar target (1080p dsb.) terikat ke TrackGroup yang valid.
                // Proteksi boolean atomik mencegah loop rekursif pemanggilan setTrackSelectionParameters
                // yang menyebabkan decoder video terus-menerus di-flush saat pemutaran sedang berjalan.
                if (!hasAppliedTrackSelectionForStream && !tracks.isEmpty() && activeQuality != null && player != null) {
                    hasAppliedTrackSelectionForStream = true;
                    applyHlsTrackSelection(activeQuality);
                }
            }

            @Override
            public void onPlaybackStateChanged(int playbackState) {
                if (playbackState == Player.STATE_BUFFERING) {
                    if (layoutBuffering != null) {
                        layoutBuffering.setVisibility(View.VISIBLE);
                        if (tvBufferingText != null) {
                            tvBufferingText.setText("MEMUAT STREAM...");
                            tvBufferingText.setVisibility(View.VISIBLE);
                        }
                    }
                } else if (playbackState == Player.STATE_READY) {
                    consecutiveRecoveryAttempts = 0;
                    hasAutoRetriedStream = false;
                    hasFallbackAttempted = false;
                    if (layoutBuffering != null) {
                        layoutBuffering.setVisibility(View.GONE);
                    }
                    if (pendingResumePosMs > 0 && player != null) {
                        player.seekTo(pendingResumePosMs);
                        pendingResumePosMs = -1;
                    }
                    if (hapticGenerator == null && player != null) {
                        int sessionId = player.getAudioSessionId();
                        if (sessionId != C.AUDIO_SESSION_ID_UNSET && sessionId > 0) {
                            currentAudioSessionId = sessionId;
                            setupHapticGenerator(sessionId);
                        }
                    }
                } else if (playbackState == Player.STATE_ENDED) {
                    if (layoutBuffering != null) {
                        layoutBuffering.setVisibility(View.GONE);
                    }
                    try {
                        SharedPreferences sp = getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
                        sp.edit().putLong("prog_" + slug + "_" + ep, 0).apply();
                    } catch (Throwable ignored) {}
                    if (hasNextEpisode()) {
                        Toast.makeText(PlayerActivity.this, "Episode selesai. Memutar Episode " + getNextEpisodeNumber() + "...", Toast.LENGTH_SHORT).show();
                        playNextEpisode();
                    }
                }
            }

            @Override
            public void onIsPlayingChanged(boolean isPlaying) {
                isVideoPlaying = isPlaying;
                if (isPlaying) {
                    handler.removeCallbacks(subtitleSyncRunnable);
                    handler.post(subtitleSyncRunnable);
                }
                if (playerView != null) {
                    playerView.setKeepScreenOn(isPlaying);
                }
                updateHapticGeneratorState();
                updateExoButtonStates();
                if (isPipSupported()) {
                    updatePipParams();
                }
            }

            @Override
            public void onPositionDiscontinuity(Player.PositionInfo oldPosition, Player.PositionInfo newPosition, int reason) {
                handler.post(subtitleSyncRunnable);
            }

            @Override
            public void onVideoSizeChanged(androidx.media3.common.VideoSize videoSize) {
                if (playerView != null) {
                    playerView.setResizeMode(currentResizeMode);
                    View sv = playerView.getVideoSurfaceView();
                    if (sv != null) {
                        sv.requestLayout();
                    }
                    playerView.requestLayout();
                }
                if (isPipSupported()) {
                    updatePipParams();
                }
            }

            @Override
            public void onPlayerError(PlaybackException error) {
                if (consecutiveRecoveryAttempts < MAX_RECOVERY_ATTEMPTS) {
                    consecutiveRecoveryAttempts++;
                    runOnUiThread(() -> {
                        Toast.makeText(PlayerActivity.this, "Stream terputus upstream, memulihkan tautan (" + consecutiveRecoveryAttempts + "/" + MAX_RECOVERY_ATTEMPTS + ")...", Toast.LENGTH_SHORT).show();
                        resolveAndPlayStream(currentResolveLoadId, true);
                    });
                    return;
                }
                if (layoutBuffering != null) {
                    layoutBuffering.setVisibility(View.GONE);
                }
                String msg = error.getMessage();
                Throwable cause = error.getCause();
                if (cause != null && cause.getMessage() != null) {
                    msg += " (" + cause.getMessage() + ")";
                }
                Toast.makeText(PlayerActivity.this, "Gagal memutar stream setelah pemulihan. Silakan ganti server atau resolusi.", Toast.LENGTH_LONG).show();
            }
        });

        playerView.setControllerVisibilityListener((PlayerView.ControllerVisibilityListener) visibility -> {
            boolean isVisible = (visibility == View.VISIBLE);
            boolean isLandscape = TvFocusHelper.isTv(this) || getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
            if (layoutTopBar != null) {
                // Di mode portrait mobile, layoutTopBar MUTLAK GONE agar tidak menutupi panggung video
                layoutTopBar.setVisibility(isLandscape ? visibility : View.GONE);
            }
            if (btnScreenLock != null && !TvFocusHelper.isTv(this)) {
                btnScreenLock.setVisibility(isVisible && !isScreenLocked && isLandscape ? View.VISIBLE : View.GONE);
            }
            if (isVisible) {
                handler.removeCallbacks(hideTopBarRunnable);
                handler.postDelayed(hideTopBarRunnable, 5000);
                bindExoControlButtons();
                updateExoButtonStates();
                if (btnExoSub != null) {
                    btnExoSub.setVisibility(View.VISIBLE);
                }
                if (btnExoSettings != null) {
                    btnExoSettings.setVisibility(View.VISIBLE);
                }
            } else {
                applySystemUiVisibility();
            }
        });
    }

    private void setupGestureControls() {
        gestureDetector = new GestureDetector(this, new GestureDetector.SimpleOnGestureListener() {
            @Override
            public boolean onSingleTapConfirmed(MotionEvent e) {
                boolean isLandscape = TvFocusHelper.isTv(PlayerActivity.this) || getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
                if (!isLandscape) {
                    if (playerView != null) {
                        if (playerView.isControllerFullyVisible()) {
                            playerView.hideController();
                        } else {
                            playerView.showController();
                        }
                    }
                    return true;
                }
                // Toggle visibility top bar (Khusus landscape / TV)
                if (layoutTopBar != null) {
                    if (layoutTopBar.getVisibility() == View.VISIBLE) {
                        layoutTopBar.setVisibility(View.GONE);
                        applySystemUiVisibility();
                    } else {
                        layoutTopBar.setVisibility(View.VISIBLE);
                        handler.postDelayed(() -> {
                            if (player != null && player.isPlaying()) {
                                layoutTopBar.setVisibility(View.GONE);
                                applySystemUiVisibility();
                            }
                        }, 4000);
                    }
                }
                return true;
            }

            @Override
            public boolean onDoubleTap(MotionEvent e) {
                float screenWidth = playerView.getWidth();
                float x = e.getX();

                if (x < screenWidth * 0.35f) {
                    seekRelative(-5000);
                    showRipple(tvRippleLeft);
                } else if (x > screenWidth * 0.65f) {
                    seekRelative(5000);
                    showRipple(tvRippleRight);
                } else {
                    if (player.isPlaying()) {
                        player.pause();
                    } else {
                        player.play();
                    }
                }
                performHapticClick();
                return true;
            }

            @Override
            public void onLongPress(MotionEvent e) {
                if (TvFocusHelper.isTv(PlayerActivity.this) || isScreenLocked || player == null) return;
                if (activeGestureZone != 0) return;

                float screenWidth = playerView.getWidth();
                if (screenWidth <= 0) return;
                float x = e.getX();

                if (x >= screenWidth * 0.5f) {
                    startHoldingSpeed();
                } else {
                    startHoldingRewind();
                }
            }

            @Override
            public boolean onScroll(MotionEvent e1, MotionEvent e2, float distanceX, float distanceY) {
                if (TvFocusHelper.isTv(PlayerActivity.this)) return false;
                if (isHoldingSpeed || isHoldingRewind) return true;
                if (e1 == null || e2 == null || playerView == null) return false;

                float viewHeight = playerView.getHeight();
                float viewWidth = playerView.getWidth();
                if (viewHeight <= 0 || viewWidth <= 0) return false;

                // Exclusion zones: cegah pemicuan volume/kecerahan saat pengguna menarik bilah notifikasi/jam di atas atau bilah navigasi di bawah
                float topExclusion = Math.max(dpToPx(56), viewHeight * 0.16f);
                float bottomExclusion = viewHeight - Math.max(dpToPx(44), viewHeight * 0.12f);
                if (e1.getY() < topExclusion || e1.getY() > bottomExclusion) {
                    return false;
                }

                // Disambiguasi awal dan penguncian zona (Edge zoning: kiri 35% kecerahan, kanan 35% volume, tengah 30% deadzone)
                if (activeGestureZone == 0) {
                    float totalDeltaY = Math.abs(e1.getY() - e2.getY());
                    float totalDeltaX = Math.abs(e1.getX() - e2.getX());
                    if (totalDeltaY < dpToPx(14) || totalDeltaY <= totalDeltaX * 1.25f) {
                        return false;
                    }
                    if (e1.getX() <= viewWidth * 0.35f) {
                        activeGestureZone = 1;
                    } else if (e1.getX() >= viewWidth * 0.65f) {
                        activeGestureZone = 2;
                    } else {
                        // Deadzone di tengah layar (35% s/d 65% lebar layar)
                        return false;
                    }
                }

                // Eksekusi penyesuaian nilai sesuai zona yang terkunci
                if (activeGestureZone == 1) {
                    adjustBrightness(distanceY / viewHeight);
                    return true;
                } else if (activeGestureZone == 2) {
                    adjustVolume(distanceY / viewHeight);
                    return true;
                }
                return false;
            }
        });

        playerView.setOnTouchListener((v, event) -> {
            if (isScreenLocked) {
                if (event.getAction() == MotionEvent.ACTION_UP) {
                    showUnlockButtonBriefly();
                }
                return true;
            }
            if (event.getAction() == MotionEvent.ACTION_DOWN) {
                activeGestureZone = 0;
                if (audioManager != null) {
                    int maxVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
                    int curVol = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC);
                    currentVolumeFraction = maxVol > 0 ? ((float) curVol / (float) maxVol) : 0f;
                }
                lastHapticBrightnessStep = (int) (currentBrightness * 100) / 5;
            } else if (event.getAction() == MotionEvent.ACTION_UP || event.getAction() == MotionEvent.ACTION_CANCEL) {
                currentVolumeFraction = -1f;
                activeGestureZone = 0;
                if (isHoldingSpeed) {
                    stopHoldingSpeed();
                }
                if (isHoldingRewind) {
                    stopHoldingRewind();
                }
            }
            boolean handled = gestureDetector.onTouchEvent(event);
            return handled || activeGestureZone != 0 || isHoldingSpeed || isHoldingRewind;
        });
    }

    private final Runnable holdRewindRunnable = new Runnable() {
        @Override
        public void run() {
            if (!isHoldingRewind || player == null) return;
            long curPos = player.getCurrentPosition();
            long newPos = Math.max(0, curPos - 2000);
            player.seekTo(newPos);
            holdRewindAccumMs += 2000;

            if (tvHoldSpeedText != null) {
                int sec = holdRewindAccumMs / 1000;
                tvHoldSpeedText.setText("Rewind (-" + sec + "s) <<");
            }
            handler.postDelayed(this, 180);
        }
    };

    private void startHoldingSpeed() {
        if (player == null || isHoldingSpeed || isHoldingRewind) return;
        isHoldingSpeed = true;
        holdOriginalSpeed = currentPlaybackSpeed;
        float boostSpeed = holdOriginalSpeed >= 2.0f ? 3.0f : 2.0f;
        player.setPlaybackParameters(new PlaybackParameters(boostSpeed));

        if (hudHoldSpeed != null) {
            if (tvHoldSpeedIcon != null) tvHoldSpeedIcon.setText("⚡");
            if (tvHoldSpeedText != null) tvHoldSpeedText.setText(String.format(java.util.Locale.US, "%.0fX Cepat >>", boostSpeed));
            hudHoldSpeed.setVisibility(View.VISIBLE);
        }
        performHapticClick();
    }

    private void stopHoldingSpeed() {
        if (!isHoldingSpeed) return;
        isHoldingSpeed = false;
        if (player != null) {
            player.setPlaybackParameters(new PlaybackParameters(holdOriginalSpeed > 0 ? holdOriginalSpeed : 1.0f));
        }
        if (hudHoldSpeed != null) {
            hudHoldSpeed.setVisibility(View.GONE);
        }
        performHapticClick();
    }

    private void startHoldingRewind() {
        if (player == null || isHoldingSpeed || isHoldingRewind) return;
        isHoldingRewind = true;
        holdRewindAccumMs = 0;

        if (hudHoldSpeed != null) {
            if (tvHoldSpeedIcon != null) tvHoldSpeedIcon.setText("⏪");
            if (tvHoldSpeedText != null) tvHoldSpeedText.setText("Rewind (0s) <<");
            hudHoldSpeed.setVisibility(View.VISIBLE);
        }
        performHapticClick();
        handler.post(holdRewindRunnable);
    }

    private void stopHoldingRewind() {
        if (!isHoldingRewind) return;
        isHoldingRewind = false;
        handler.removeCallbacks(holdRewindRunnable);
        if (hudHoldSpeed != null) {
            hudHoldSpeed.setVisibility(View.GONE);
        }
        performHapticClick();
    }

    private void lockScreen() {
        if (TvFocusHelper.isTv(this)) return;
        isScreenLocked = true;
        if (playerView != null) {
            playerView.hideController();
            playerView.setUseController(false);
        }
        if (layoutTopBar != null) {
            layoutTopBar.setVisibility(View.GONE);
        }
        if (btnSkipOpEd != null) {
            btnSkipOpEd.setVisibility(View.GONE);
        }
        if (btnScreenLock != null) {
            btnScreenLock.setVisibility(View.GONE);
        }
        performHapticHeavyClick();
        Toast.makeText(this, "Layar terkunci. Ketuk layar untuk membuka kunci.", Toast.LENGTH_SHORT).show();
        showUnlockButtonBriefly();
    }

    private void unlockScreen() {
        isScreenLocked = false;
        if (btnScreenUnlock != null) {
            handler.removeCallbacks(hideUnlockButtonRunnable);
            btnScreenUnlock.setVisibility(View.GONE);
        }
        if (playerView != null) {
            playerView.setUseController(true);
            playerView.showController();
        }
        showTopBarBriefly();
        if (btnScreenLock != null && !TvFocusHelper.isTv(this)) {
            btnScreenLock.setVisibility(View.VISIBLE);
        }
        performHapticClick();
        Toast.makeText(this, "Layar terbuka", Toast.LENGTH_SHORT).show();
    }

    private void showUnlockButtonBriefly() {
        if (btnScreenUnlock == null || !isScreenLocked || TvFocusHelper.isTv(this)) return;
        btnScreenUnlock.animate().cancel();
        btnScreenUnlock.setAlpha(1.0f);
        btnScreenUnlock.setVisibility(View.VISIBLE);
        handler.removeCallbacks(hideUnlockButtonRunnable);
        handler.postDelayed(hideUnlockButtonRunnable, 3000);
    }

    private final Runnable hideTopBarRunnable = this::hideTopBar;

    private void showTopBarBriefly() {
        boolean isLandscape = TvFocusHelper.isTv(this) || getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
        if (!isLandscape) {
            if (layoutTopBar != null) layoutTopBar.setVisibility(View.GONE);
            return;
        }
        if (layoutTopBar != null) {
            layoutTopBar.setVisibility(View.VISIBLE);
            handler.removeCallbacks(hideTopBarRunnable);
            handler.postDelayed(hideTopBarRunnable, 5000);
        }
        if (btnScreenLock != null && !TvFocusHelper.isTv(this) && !isScreenLocked) {
            btnScreenLock.setVisibility(View.VISIBLE);
        }
    }

    private void hideTopBar() {
        if (layoutTopBar != null) {
            layoutTopBar.setVisibility(View.GONE);
            if (btnScreenLock != null) {
                btnScreenLock.setVisibility(View.GONE);
            }
            if (playerView != null) {
                playerView.requestFocus();
            }
            applySystemUiVisibility();
        }
    }

    private boolean isViewOrChildFocused(View parent) {
        if (parent == null || parent.getVisibility() != View.VISIBLE) return false;
        if (parent.isFocused()) return true;
        if (parent instanceof ViewGroup) {
            View current = getCurrentFocus();
            if (current != null) {
                View p = current;
                while (p != null) {
                    if (p == parent) return true;
                    if (p.getParent() instanceof View) {
                        p = (View) p.getParent();
                    } else {
                        break;
                    }
                }
            }
        }
        return false;
    }

    private boolean isChildOf(View child, View parent) {
        if (child == null || parent == null) return false;
        if (child == parent) return true;
        View p = child;
        while (p != null) {
            if (p == parent) return true;
            if (p.getParent() instanceof View) {
                p = (View) p.getParent();
            } else {
                break;
            }
        }
        return false;
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            int keyCode = event.getKeyCode();

            if (isScreenLocked) {
                if (keyCode == KeyEvent.KEYCODE_BACK) {
                    showUnlockButtonBriefly();
                    Toast.makeText(this, "Layar terkunci. Buka kunci layar terlebih dahulu.", Toast.LENGTH_SHORT).show();
                    return true;
                }
                if (keyCode == KeyEvent.KEYCODE_VOLUME_UP || keyCode == KeyEvent.KEYCODE_VOLUME_DOWN || keyCode == KeyEvent.KEYCODE_VOLUME_MUTE) {
                    return super.dispatchKeyEvent(event);
                }
                return true;
            }

            boolean isTopBarActive = (layoutTopBar != null && layoutTopBar.getVisibility() == View.VISIBLE);
            boolean hasFocusOnTopBar = isTopBarActive && isViewOrChildFocused(layoutTopBar);
            boolean isSkipVisible = (btnSkipOpEd != null && btnSkipOpEd.getVisibility() == View.VISIBLE);
            boolean isSkipFocused = isSkipVisible && (btnSkipOpEd.isFocused() || getCurrentFocus() == btnSkipOpEd);

            switch (keyCode) {
                case KeyEvent.KEYCODE_MENU:
                case KeyEvent.KEYCODE_SETTINGS:
                case KeyEvent.KEYCODE_INFO:
                    showPlayerUnifiedSettingsDialog();
                    return true;

                case KeyEvent.KEYCODE_DPAD_CENTER:
                case KeyEvent.KEYCODE_ENTER:
                    if (isSkipFocused) {
                        doSkipOpEd();
                        return true;
                    }
                    if (hasFocusOnTopBar) {
                        View focused = getCurrentFocus();
                        if (focused != null && isChildOf(focused, layoutTopBar)) {
                            showTopBarBriefly();
                            focused.performClick();
                            return true;
                        }
                    }
                    View focused = getCurrentFocus();
                    if (focused != null && focused != playerView) {
                        if (focused == btnExoNext || (btnExoNext != null && focused.getId() == androidx.media3.ui.R.id.exo_next)) {
                            playNextEpisode();
                            return true;
                        }
                        if (focused == btnExoPrev || (btnExoPrev != null && focused.getId() == androidx.media3.ui.R.id.exo_prev)) {
                            playPrevEpisode();
                            return true;
                        }
                        if (playerView != null && isChildOf(focused, playerView) && focused.isClickable()) {
                            focused.performClick();
                            return true;
                        }
                    }
                    boolean isHudVisible = isTopBarActive || (playerView != null && playerView.isControllerFullyVisible());
                    if (!isHudVisible && isSkipVisible) {
                        doSkipOpEd();
                        return true;
                    }
                    if (player != null) {
                        if (player.isPlaying()) {
                            player.pause();
                            showTopBarBriefly();
                            if (playerView != null) {
                                playerView.showController();
                            }
                            updateExoButtonStates();
                            if (TvFocusHelper.isTv(this)) {
                                if (btnExoNext != null && btnExoNext.isEnabled()) {
                                    btnExoNext.requestFocus();
                                } else if (btnSkipOpEd != null && btnSkipOpEd.getVisibility() == View.VISIBLE) {
                                    btnSkipOpEd.requestFocus();
                                }
                            }
                        } else {
                            player.play();
                            hideTopBar();
                        }
                        vibrate(20);
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
                    if (player != null) {
                        if (player.isPlaying()) {
                            player.pause();
                            showTopBarBriefly();
                            if (playerView != null) {
                                playerView.showController();
                            }
                            updateExoButtonStates();
                            if (TvFocusHelper.isTv(this)) {
                                if (btnExoNext != null && btnExoNext.isEnabled()) {
                                    btnExoNext.requestFocus();
                                } else if (btnSkipOpEd != null && btnSkipOpEd.getVisibility() == View.VISIBLE) {
                                    btnSkipOpEd.requestFocus();
                                }
                            }
                        } else {
                            player.play();
                            hideTopBar();
                        }
                        vibrate(20);
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_MEDIA_PLAY:
                    if (player != null && !player.isPlaying()) {
                        player.play();
                        hideTopBar();
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_MEDIA_PAUSE:
                    if (player != null && player.isPlaying()) {
                        player.pause();
                        showTopBarBriefly();
                        if (playerView != null) {
                            playerView.showController();
                        }
                        updateExoButtonStates();
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_MEDIA_NEXT:
                case KeyEvent.KEYCODE_PAGE_DOWN:
                case KeyEvent.KEYCODE_N:
                    if (hasNextEpisode()) {
                        playNextEpisode();
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_MEDIA_PREVIOUS:
                case KeyEvent.KEYCODE_PAGE_UP:
                case KeyEvent.KEYCODE_P:
                    if (hasPrevEpisode()) {
                        playPrevEpisode();
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_DPAD_LEFT:
                    if (isSkipFocused && playerView != null) {
                        playerView.requestFocus();
                    }
                    boolean isTvLeft = TvFocusHelper.isTv(this);
                    boolean isPlayingLeft = (player != null && player.isPlaying());
                    if (isTvLeft && !isPlayingLeft) {
                        // Di Android TV saat video ter-pause: D-Pad Kiri mengarahkan ke Prev Episode atau Play
                        if (hasFocusOnTopBar) {
                            showTopBarBriefly();
                            break; // Biarkan navigasi horizontal antar tombol header di top bar
                        }
                        if (playerView != null) {
                            playerView.showController();
                        }
                        View currentFocused = getCurrentFocus();
                        if (currentFocused == btnSkipOpEd && btnExoNext != null && btnExoNext.isEnabled()) {
                            btnExoNext.requestFocus();
                            return true;
                        }
                        if (currentFocused == btnExoNext) {
                            View playBtn = playerView != null ? playerView.findViewById(androidx.media3.ui.R.id.exo_play_pause) : null;
                            if (playBtn == null && playerView != null) playBtn = playerView.findViewById(androidx.media3.ui.R.id.exo_play);
                            if (playBtn != null && playBtn.getVisibility() == View.VISIBLE) {
                                playBtn.requestFocus();
                                return true;
                            }
                        }
                        if (btnExoPrev != null && btnExoPrev.isEnabled() && currentFocused != btnExoPrev) {
                            btnExoPrev.requestFocus();
                            return true;
                        }
                        View playBtn = playerView != null ? playerView.findViewById(androidx.media3.ui.R.id.exo_play_pause) : null;
                        if (playBtn == null && playerView != null) playBtn = playerView.findViewById(androidx.media3.ui.R.id.exo_play);
                        if (playBtn != null && playBtn.getVisibility() == View.VISIBLE) {
                            playBtn.requestFocus();
                            return true;
                        }
                        break;
                    }
                    if (hasFocusOnTopBar) {
                        showTopBarBriefly();
                        break; // Jangan seek, biarkan navigasi fokus antar tombol
                    }
                    seekRelative(-5000);
                    showRipple(tvRippleLeft);
                    vibrate(15);
                    return true;

                case KeyEvent.KEYCODE_MEDIA_REWIND:
                    seekRelative(-5000);
                    showRipple(tvRippleLeft);
                    vibrate(15);
                    return true;

                case KeyEvent.KEYCODE_DPAD_RIGHT:
                    if (isSkipFocused && playerView != null) {
                        playerView.requestFocus();
                    }
                    boolean isTvRight = TvFocusHelper.isTv(this);
                    boolean isPlayingRight = (player != null && player.isPlaying());
                    if (isTvRight && !isPlayingRight) {
                        // Di Android TV saat video ter-pause: D-Pad Kanan mengarahkan ke Next Episode atau Skip Op/Ed
                        if (hasFocusOnTopBar) {
                            showTopBarBriefly();
                            break; // Biarkan navigasi horizontal antar tombol header di top bar
                        }
                        if (playerView != null) {
                            playerView.showController();
                        }
                        View currentFocused = getCurrentFocus();
                        if (currentFocused == btnExoPrev) {
                            View playBtn = playerView != null ? playerView.findViewById(androidx.media3.ui.R.id.exo_play_pause) : null;
                            if (playBtn == null && playerView != null) playBtn = playerView.findViewById(androidx.media3.ui.R.id.exo_play);
                            if (playBtn != null && playBtn.getVisibility() == View.VISIBLE) {
                                playBtn.requestFocus();
                                return true;
                            }
                        }
                        if (isSkipVisible && currentFocused == btnExoNext) {
                            btnSkipOpEd.requestFocus();
                            return true;
                        }
                        if (btnExoNext != null && btnExoNext.isEnabled() && currentFocused != btnExoNext) {
                            btnExoNext.requestFocus();
                            return true;
                        }
                        if (isSkipVisible && currentFocused != btnSkipOpEd) {
                            btnSkipOpEd.requestFocus();
                            return true;
                        }
                        break;
                    }
                    if (hasFocusOnTopBar) {
                        showTopBarBriefly();
                        break; // Jangan seek, biarkan navigasi fokus antar tombol
                    }
                    seekRelative(5000);
                    showRipple(tvRippleRight);
                    vibrate(15);
                    return true;

                case KeyEvent.KEYCODE_MEDIA_FAST_FORWARD:
                case KeyEvent.KEYCODE_BUTTON_R1:
                    if (isSkipVisible) {
                        doSkipOpEd();
                        return true;
                    }
                    seekRelative(5000);
                    showRipple(tvRippleRight);
                    vibrate(15);
                    return true;

                case KeyEvent.KEYCODE_DPAD_UP:
                    if (TvFocusHelper.isTv(this)) {
                        showTopBarBriefly();
                        if (btnSubSelector != null && btnSubSelector.getVisibility() == View.VISIBLE) {
                            btnSubSelector.requestFocus();
                            return true;
                        } else if (btnQuality != null && btnQuality.getVisibility() == View.VISIBLE) {
                            btnQuality.requestFocus();
                            return true;
                        } else if (btnAspect != null && btnAspect.getVisibility() == View.VISIBLE) {
                            btnAspect.requestFocus();
                            return true;
                        } else if (btnPlayerBack != null) {
                            btnPlayerBack.requestFocus();
                            return true;
                        }
                    }
                    if (isSkipFocused) {
                        showTopBarBriefly();
                        if (btnSubSelector != null && btnSubSelector.getVisibility() == View.VISIBLE) {
                            btnSubSelector.requestFocus();
                        } else if (playerView != null) {
                            playerView.requestFocus();
                        }
                        return true;
                    }
                    showTopBarBriefly();
                    if (btnSubSelector != null && btnSubSelector.getVisibility() == View.VISIBLE) {
                        btnSubSelector.requestFocus();
                        return true;
                    }
                    if (playerView != null) {
                        playerView.showController();
                    }
                    break;

                case KeyEvent.KEYCODE_DPAD_DOWN:
                    if (TvFocusHelper.isTv(this)) {
                        if (isTopBarActive) {
                            hideTopBar();
                        }
                        if (playerView != null) {
                            playerView.showController();
                        }
                        if (isSkipVisible && !isSkipFocused) {
                            btnSkipOpEd.requestFocus();
                            boolean inIntro = (introEndMs > introStartMs && player != null
                                    && player.getCurrentPosition() >= introStartMs && player.getCurrentPosition() < introEndMs);
                            updateSkipButtonLabel(inIntro);
                            return true;
                        }
                        if (btnExoNext != null && btnExoNext.isEnabled() && btnExoNext.getVisibility() == View.VISIBLE) {
                            btnExoNext.requestFocus();
                            return true;
                        }
                        View playBtn = playerView != null ? playerView.findViewById(androidx.media3.ui.R.id.exo_play_pause) : null;
                        if (playBtn == null && playerView != null) playBtn = playerView.findViewById(androidx.media3.ui.R.id.exo_play);
                        if (playBtn != null && playBtn.getVisibility() == View.VISIBLE) {
                            playBtn.requestFocus();
                            return true;
                        }
                        return true;
                    }
                    if (isSkipFocused) {
                        if (playerView != null) playerView.requestFocus();
                        if (playerView != null) {
                            if (playerView.isControllerFullyVisible()) {
                                playerView.hideController();
                            } else {
                                playerView.showController();
                            }
                        }
                        return true;
                    }
                    if (isTopBarActive) {
                        hideTopBar();
                        return true;
                    }
                    if (playerView != null) {
                        if (playerView.isControllerFullyVisible()) {
                            playerView.hideController();
                        } else {
                            playerView.showController();
                        }
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_BACK:
                    if (isSkipFocused) {
                        if (playerView != null) playerView.requestFocus();
                        boolean inIntro = (introEndMs > introStartMs && player != null
                                && player.getCurrentPosition() >= introStartMs && player.getCurrentPosition() < introEndMs);
                        updateSkipButtonLabel(inIntro);
                        return true;
                    }
                    if (isTopBarActive) {
                        hideTopBar();
                        return true;
                    }
                    break;
            }
        }
        return super.dispatchKeyEvent(event);
    }

    private void seekRelative(long deltaMs) {
        if (player != null) {
            long newPos = Math.max(0, Math.min(player.getDuration(), player.getCurrentPosition() + deltaMs));
            player.seekTo(newPos);
            handler.post(subtitleSyncRunnable);
        }
    }

    private void adjustVolume(float percent) {
        if (audioManager == null) return;
        int maxVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
        if (maxVol <= 0) return;

        if (currentVolumeFraction < 0) {
            int curVol = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC);
            currentVolumeFraction = (float) curVol / (float) maxVol;
        }

        // Akumulator float kontinu (sama seperti brightness) agar gerakan lambat tidak terpotong menjadi 0
        currentVolumeFraction = Math.max(0.0f, Math.min(1.0f, currentVolumeFraction + (percent * 0.85f)));
        int targetVol = Math.round(currentVolumeFraction * maxVol);
        int curVol = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC);
        if (targetVol != curVol) {
            audioManager.setStreamVolume(AudioManager.STREAM_MUSIC, targetVol, 0);
            performHapticTick();
        }

        int pct = Math.round(currentVolumeFraction * 100);
        showOsd(targetVol == 0 ? "MUTE" : "VOL", pct);
    }

    private void adjustBrightness(float percent) {
        currentBrightness = Math.max(0.05f, Math.min(1.0f, currentBrightness + (percent * 0.85f)));
        WindowManager.LayoutParams lp = getWindow().getAttributes();
        lp.screenBrightness = currentBrightness;
        getWindow().setAttributes(lp);

        int pct = (int) (currentBrightness * 100);
        int step = pct / 5;
        if (step != lastHapticBrightnessStep) {
            lastHapticBrightnessStep = step;
            performHapticTick();
        }
        showOsd("BRT", pct);
    }

    private void showOsd(String icon, int pct) {
        tvOsdIcon.setText(icon);
        pbOsdBar.setProgress(pct);
        tvOsdVal.setText(pct + "%");
        hudOsd.setVisibility(View.VISIBLE);
        handler.removeCallbacks(hideOsdRunnable);
        handler.postDelayed(hideOsdRunnable, 1200);
    }

    private final Runnable hideOsdRunnable = () -> hudOsd.setVisibility(View.GONE);

    private void showRipple(TextView tv) {
        tv.setVisibility(View.VISIBLE);
        handler.postDelayed(() -> tv.setVisibility(View.GONE), 350);
    }

    private Vibrator cachedVibrator = null;

    private Vibrator getVibratorService() {
        if (cachedVibrator != null) return cachedVibrator;
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                android.os.VibratorManager vm = (android.os.VibratorManager) getSystemService(Context.VIBRATOR_MANAGER_SERVICE);
                if (vm != null) {
                    Vibrator defVib = vm.getDefaultVibrator();
                    if (defVib != null && defVib.hasVibrator()) {
                        cachedVibrator = defVib;
                        return cachedVibrator;
                    }
                }
            }
            cachedVibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            return cachedVibrator;
        } catch (Throwable t) {
            try {
                cachedVibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
                return cachedVibrator;
            } catch (Throwable ignored) {
                return null;
            }
        }
    }

    private void vibrateDirect(long ms, int amplitude) {
        if (!isHapticEnabled || TvFocusHelper.isTv(this)) return;
        try {
            Vibrator v = getVibratorService();
            if (v == null || !v.hasVibrator()) {
                v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
                if (v == null || !v.hasVibrator()) return;
            }

            boolean hasAmp = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && v.hasAmplitudeControl();
            long effectiveMs = ms;
            // Adaptasi durasi untuk motor ERM (Samsung Galaxy A-series, Redmi, Poco, dll.)
            // Motor ERM koin memiliki inersia fisik ~35-50ms sebelum massa eksentrik mulai berputar.
            // Tanpa amplitudo kontrol (hasAmp == false), pulsa dinaikkan agar getaran terasa jelas di tangan.
            if (!hasAmp) {
                if (ms <= 20) {
                    effectiveMs = 45; // Tick terasa di ERM
                } else if (ms <= 30) {
                    effectiveMs = 65; // Click terasa di ERM
                } else if (ms <= 50) {
                    effectiveMs = 90; // Heavy click terasa di ERM
                } else {
                    effectiveMs = Math.max(ms, 80); // Scene hit / ledakan di ERM
                }
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                int amp = VibrationEffect.DEFAULT_AMPLITUDE;
                if (amplitude > 0 && amplitude <= 255 && hasAmp) {
                    amp = amplitude;
                }
                VibrationEffect effect = VibrationEffect.createOneShot(effectiveMs, amp);
                try {
                    // Gunakan USAGE_MEDIA agar lolos dari penyaringan sistem Samsung One UI
                    // untuk feedback sentuh dan terikat dengan kanal playback media video aktif.
                    android.media.AudioAttributes attrs = new android.media.AudioAttributes.Builder()
                            .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION)
                            .setUsage(android.media.AudioAttributes.USAGE_MEDIA)
                            .build();
                    v.vibrate(effect, attrs);
                } catch (Throwable fallbackAttr) {
                    v.vibrate(effect);
                }
            } else {
                v.vibrate(effectiveMs);
            }
        } catch (Throwable ignored) {}
    }

    private void performHapticTick() {
        if (!isHapticEnabled || TvFocusHelper.isTv(this)) return;
        try {
            if (playerView != null) {
                playerView.performHapticFeedback(
                    Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE
                        ? HapticFeedbackConstants.SEGMENT_TICK
                        : (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R
                            ? HapticFeedbackConstants.CLOCK_TICK
                            : HapticFeedbackConstants.KEYBOARD_TAP),
                    HapticFeedbackConstants.FLAG_IGNORE_VIEW_SETTING | HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING
                );
            }
        } catch (Throwable ignored) {}
        vibrateDirect(15, 70);
    }

    private void performHapticClick() {
        if (!isHapticEnabled || TvFocusHelper.isTv(this)) return;
        try {
            if (playerView != null) {
                playerView.performHapticFeedback(
                    HapticFeedbackConstants.KEYBOARD_TAP,
                    HapticFeedbackConstants.FLAG_IGNORE_VIEW_SETTING | HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING
                );
            }
        } catch (Throwable ignored) {}
        vibrateDirect(25, 140);
    }

    private void performHapticHeavyClick() {
        if (!isHapticEnabled || TvFocusHelper.isTv(this)) return;
        try {
            if (playerView != null) {
                playerView.performHapticFeedback(
                    Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE
                        ? HapticFeedbackConstants.DRAG_START
                        : HapticFeedbackConstants.LONG_PRESS,
                    HapticFeedbackConstants.FLAG_IGNORE_VIEW_SETTING | HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING
                );
            }
        } catch (Throwable ignored) {}
        vibrateDirect(45, 230);
    }

    private void vibrate(long ms) {
        if (!isHapticEnabled || TvFocusHelper.isTv(this)) return;
        vibrateDirect(ms > 0 ? ms : 25, -1);
    }

    private void setupHapticGenerator(int audioSessionId) {
        if (TvFocusHelper.isTv(this)) return;
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return;
        if (audioSessionId == C.AUDIO_SESSION_ID_UNSET || audioSessionId <= 0) return;

        releaseHapticGenerator();

        try {
            hapticGenerator = HapticGeneratorHelper.create(audioSessionId);
            updateHapticGeneratorState();
        } catch (Throwable t) {
            hapticGenerator = null;
        }
    }

    private void updateHapticGeneratorState() {
        if (TvFocusHelper.isTv(this)) return;
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return;
        if (hapticGenerator instanceof HapticGenerator) {
            // Isolasi getaran adegan: HapticGenerator bawaan Android dinonaktifkan (false)
            // agar tidak bergetar secara buta mengikuti bass background music (BGM/OST).
            // Seluruh haptic scene dikendalikan secara presisi oleh SceneHapticAudioSink.
            HapticGeneratorHelper.setEnabled((HapticGenerator) hapticGenerator, false);
        }
    }

    private void releaseHapticGenerator() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return;
        if (hapticGenerator instanceof HapticGenerator) {
            HapticGeneratorHelper.release((HapticGenerator) hapticGenerator);
            hapticGenerator = null;
        }
    }

    @androidx.annotation.RequiresApi(Build.VERSION_CODES.S)
    private static class HapticGeneratorHelper {
        static HapticGenerator create(int audioSessionId) {
            try {
                if (HapticGenerator.isAvailable()) {
                    return HapticGenerator.create(audioSessionId);
                }
            } catch (Throwable ignored) {}
            return null;
        }

        static void setEnabled(HapticGenerator generator, boolean enabled) {
            if (generator != null) {
                try {
                    generator.setEnabled(enabled);
                } catch (Throwable ignored) {}
            }
        }

        static void release(HapticGenerator generator) {
            if (generator != null) {
                try {
                    generator.setEnabled(false);
                    generator.release();
                } catch (Throwable ignored) {}
            }
        }
    }

    private class SceneHapticAudioSink implements TeeAudioProcessor.AudioBufferSink {
        private long lastHapticTriggerWallMs = -1000;
        private long lastExplosionTriggerMs = -1000;
        private float runningRms = 1500f;
        private int prevRms = 1500;
        private float lpFilterState = 0f;
        private int currentSampleRateHz = 48000;
        private int currentChannelCount = 2;

        @Override
        public void flush(int sampleRateHz, int channelCount, int encoding) {
            runningRms = 1500f;
            prevRms = 1500;
            lpFilterState = 0f;
            currentSampleRateHz = sampleRateHz > 0 ? sampleRateHz : 48000;
            currentChannelCount = channelCount > 0 ? channelCount : 2;
        }

        @Override
        public void handleBuffer(ByteBuffer buffer) {
            if (!isSceneHapticEnabled || !isGeneralHapticEnabled || !isVideoPlaying || isInOpEd || TvFocusHelper.isTv(PlayerActivity.this)) return;

            ByteBuffer duplicate = buffer.asReadOnlyBuffer();
            duplicate.order(ByteOrder.LITTLE_ENDIAN);
            ShortBuffer shortBuffer = duplicate.asShortBuffer();
            int remaining = shortBuffer.remaining();
            if (remaining <= 0) return;

            int channels = Math.max(1, currentChannelCount);
            int totalFrames = remaining / channels;
            if (totalFrames <= 0) return;

            // Koefisien Bipolar 200Hz Low-Pass Filter: alpha = (2 * pi * fc) / fs
            float alpha = (float) ((2.0 * Math.PI * 200.0) / currentSampleRateHz);
            alpha = Math.max(0.005f, Math.min(0.2f, alpha));

            int peak = 0;
            long sumSquares = 0;
            double sumSquaresLp = 0;
            float lp = lpFilterState;

            for (int f = 0; f < totalFrames; f++) {
                int baseIdx = f * channels;
                short left = shortBuffer.get(baseIdx);
                short right = (channels > 1) ? shortBuffer.get(baseIdx + 1) : left;

                // Stereo channel fusion: baca kedua channel L dan R tanpa blind spot
                int sampleMax = Math.max(Math.abs(left), Math.abs(right));
                if (sampleMax > peak) peak = sampleMax;
                sumSquares += (long) sampleMax * sampleMax;

                // Low-pass filter pada kanal dominan akustik
                int rawDominant = (Math.abs(left) >= Math.abs(right)) ? left : right;
                lp += alpha * ((float) rawDominant - lp);
                sumSquaresLp += (double) lp * lp;
            }
            lpFilterState = lp;

            int rms = (int) Math.sqrt((double) sumSquares / totalFrames);
            int subRms = (int) Math.sqrt(sumSquaresLp / totalFrames);
            float crestFactor = (float) peak / Math.max(1f, (float) rms);
            float subRatio = (float) subRms / Math.max(1f, (float) rms);

            long nowMs = SystemClock.uptimeMillis();

            int deltaRms = rms - prevRms;
            prevRms = rms;

            float effectiveBaseline = Math.max(1200f, runningRms);
            float surgeRatio = (float) rms / effectiveBaseline;

            // 1. Anti-Scream Rejection:
            // Karakter anime berteriak (vokal murni) memiliki energi tinggi di mid-high frequencies,
            // subRatio rendah (< 0.35), dan Crest Factor rendah (< 3.0).
            boolean isVocalScream = (subRatio < 0.35f && crestFactor < 3.0f);
            if (isVocalScream) {
                runningRms = 0.88f * runningRms + 0.12f * rms;
                return;
            }

            // 2. Klasifikasi Adegan Akustik:
            // A. Gunfire / Rapid Kinetic Strike (tembakan pistol/senapan, benturan katana):
            // Transien tajam, Crest Factor tinggi (>= 3.2), lonjakan mendadak (deltaRms >= 800)
            boolean isGunshot = (crestFactor >= 3.2f && peak >= 16500 && deltaRms >= 800);

            // B. Physical Strike / Heavy Attack Onset (pukulan tinju, tendangan):
            boolean isAttackOnset = (deltaRms >= 1400 && peak >= 16500) ||
                                    (surgeRatio >= 1.55f && peak >= 17000 && rms >= 2600 && deltaRms >= 600);

            // C. Heavy Explosion / Super-Move / Colossal Blast:
            // Dentuman dahsyat (bom, sihir kehancuran). Wajib attack onset (deltaRms >= 1200)
            // agar tidak terpicu pada ekor gema / sub-bass rumble yang sedang meluruh.
            boolean isColossal = (peak >= 22000 && (rms - runningRms) >= 1200 && deltaRms >= 1200) ||
                                 (peak >= 24000 && subRms >= 7000 && subRatio >= 0.50f && deltaRms >= 1200);

            // Anti-reverb lockout: abaikan gema/asap pasca-ledakan dalam 400ms
            if (isColossal && (nowMs - lastExplosionTriggerMs < 400)) {
                runningRms = 0.88f * runningRms + 0.12f * rms;
                return;
            }

            // Dual-cadence cooldown:
            // Tembakan: cooldown pendek 85ms (mendukung burst-fire / semi-auto)
            // Benturan fisik / Ledakan: cooldown 200ms
            long minCooldownMs = isGunshot ? 85 : 200;
            if (nowMs - lastHapticTriggerWallMs < minCooldownMs) {
                runningRms = 0.88f * runningRms + 0.12f * rms;
                return;
            }

            boolean isSceneImpact = isGunshot || isAttackOnset || isColossal;
            if (!isSceneImpact) {
                runningRms = 0.88f * runningRms + 0.12f * rms;
                return;
            }

            // Catat waktu pemicuan
            lastHapticTriggerWallMs = nowMs;
            if (isColossal) {
                lastExplosionTriggerMs = nowMs;
            }
            runningRms = Math.max(runningRms, (float) rms * 0.75f);

            int intensity = Math.min(255, 140 + ((peak - 16500) * 115 / 16267));

            // Profil durasi haptik multi-tier:
            // - Tembakan: pulsa tajam 15ms
            // - Benturan fisik: 30ms
            // - Ledakan dahsyat: 45ms
            long vibeDurationMs;
            if (isColossal) {
                vibeDurationMs = 45;
                intensity = Math.max(intensity, 230);
            } else if (isGunshot) {
                vibeDurationMs = 15;
            } else {
                vibeDurationMs = 30;
            }

            // Zero-delay direct trigger: eksekusi seketika tanpa antrean postDelayed
            vibrateDirect(vibeDurationMs, intensity);
        }
    }

    private void resolveAndPlayStream() {
        resolveAndPlayStream(currentResolveLoadId, false);
    }

    private void resolveAndPlayStream(final int resolveId) {
        resolveAndPlayStream(resolveId, false);
    }

    private void resolveAndPlayStream(final int resolveId, final boolean forceRefresh) {
        runOnUiThread(() -> {
            if (layoutBuffering != null) {
                layoutBuffering.setVisibility(View.VISIBLE);
                if (tvBufferingText != null) {
                    tvBufferingText.setText(forceRefresh ? "MEMULIHKAN STREAM..." : "MENYIAPKAN STREAM...");
                    tvBufferingText.setVisibility(View.VISIBLE);
                }
            }
        });

        new Thread(() -> {
            try {
                if (resolveId != currentResolveLoadId) return;

                SharedPreferences sp = getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
                activeQuality = sp.getString("pref_quality", "best");

                String effectiveMode = (requestMode != null && !requestMode.isEmpty()) ? requestMode : "sub";
                String u = "http://127.0.0.1:8767/api/episode?slug=" + URLEncoder.encode(slug != null ? slug : "", "UTF-8")
                        + "&ep=" + ep + "&mode=" + URLEncoder.encode(effectiveMode, "UTF-8") + "&q=" + URLEncoder.encode(activeQuality != null ? activeQuality : "best", "UTF-8")
                        + (forceRefresh ? "&refresh=1&force=true" : "");
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setConnectTimeout(15000);
                conn.setReadTimeout(45000);
                int code = conn.getResponseCode();
                InputStream is = (code >= 200 && code < 400) ? conn.getInputStream() : conn.getErrorStream();
                if (is == null) {
                    throw new IOException("HTTP " + code + " tanpa respons");
                }
                BufferedReader reader = new BufferedReader(new InputStreamReader(is));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                reader.close();
                conn.disconnect();

                if (resolveId != currentResolveLoadId) return;

                JSONObject res = new JSONObject(sb.toString());
                if (res.optBoolean("success")) {
                    JSONObject data = res.getJSONObject("data");
                    activeStreamMode = data.optString("mode", "sub");
                    String streamUrl = "";
                    String masterUrl = data.optString("master", "");
                    if (!masterUrl.isEmpty()) {
                        streamUrl = masterUrl;
                    } else if (data.has("picked")) {
                        streamUrl = data.getJSONObject("picked").optString("url");
                    } else if (data.has("variants")) {
                        JSONArray vars = data.getJSONArray("variants");
                        if (vars.length() > 0) {
                            streamUrl = vars.getJSONObject(0).optString("url");
                        }
                    }
                    String referer = data.optString("referer", "");

                    // Simpan stream variants untuk selector resolusi
                    JSONArray varsArr = data.optJSONArray("variants");
                    streamVariants.clear();
                    if (varsArr != null) {
                        for (int i = 0; i < varsArr.length(); i++) {
                            streamVariants.add(varsArr.getJSONObject(i));
                        }
                    }
                    String pickedQ = "HD";
                    if (data.has("picked")) {
                        pickedQ = data.getJSONObject("picked").optString("q", "HD");
                    } else if (!streamVariants.isEmpty()) {
                        pickedQ = streamVariants.get(0).optString("q", "HD");
                    }
                    activeQuality = pickedQ;

                    isHlsMode = isHlsStream(masterUrl) || isHlsStream(streamUrl)
                            || (!streamVariants.isEmpty() && isHlsStream(streamVariants.get(0).optString("url", "")));
                    if (!forceRefresh) {
                        consecutiveRecoveryAttempts = 0;
                        hasFallbackAttempted = false;
                        hasAutoRetriedStream = false;
                    }

                    // Simpan subtitle tracks yang tersedia
                    JSONArray subArr = data.optJSONArray("subtitles");
                    String singleSub = data.optString("sub", "");
                    boolean hasValidSubs = (subArr != null && subArr.length() > 0)
                            || (!singleSub.isEmpty() && (singleSub.startsWith("http://") || singleSub.startsWith("https://") || singleSub.startsWith("/")));

                    // Jika mode adalah "sub" namun subtitle kosong dan belum di-refresh,
                    // lakukan sekali retry otomatis ke resolver dengan refresh=1 sebelum memasang MediaItem / SubtitleConfiguration
                    if ("sub".equalsIgnoreCase(effectiveMode) && !hasValidSubs && !forceRefresh) {
                        runOnUiThread(() -> {
                            if (resolveId == currentResolveLoadId) {
                                resolveAndPlayStream(resolveId, true);
                            }
                        });
                        return;
                    }

                    subtitleTracks.clear();
                    String foundEnSub = "";
                    String foundExactEnSub = "";
                    String foundAnyEnSub = "";
                    String foundIdSub = "";
                    String foundDefSub = "";
                    String foundNonArSub = "";

                    String[] nonEnKeywords = new String[]{
                        "arabic", "arab", "indonesia", "bahasa", "spanish", "espanol",
                        "portuguese", "french", "francais", "german", "deutsch", "italian",
                        "korean", "chinese", "russian", "thai", "vietnamese", "turkish",
                        "hindi", "czech", "danish", "dutch", "finnish", "greek",
                        "hungarian", "norwegian", "polish", "romanian", "slovak", "swedish",
                        "malay", "tagalog", "filipino", "japanese"
                    };

                    if (subArr != null) {
                        for (int i = 0; i < subArr.length(); i++) {
                            JSONObject s = subArr.getJSONObject(i);
                            subtitleTracks.add(s);
                            String lang = s.optString("lang", "").toLowerCase().trim();
                            String lbl = s.optString("label", "").toLowerCase().trim();
                            String url = s.optString("url", "");
                            boolean isDef = s.optBoolean("default", false);

                            boolean isArabic = lang.equals("ar") || lang.equals("ara") || lbl.contains("arabic") || lbl.contains("arab");
                            boolean isIndo = lang.equals("id") || lang.equals("ind") || lbl.contains("indonesia") || lbl.contains("bahasa");

                            boolean hasNonEnKeyword = false;
                            for (String kw : nonEnKeywords) {
                                if (lbl.contains(kw)) {
                                    hasNonEnKeyword = true;
                                    break;
                                }
                            }

                            boolean isEnglish = !hasNonEnKeyword && (lang.equals("en") || lang.equals("eng") || lbl.contains("english") || lbl.startsWith("eng"));
                            boolean isExactEnglish = isEnglish && (lbl.equals("english") || lbl.equals("english [full]") || lbl.equals("eng"));

                            if (isExactEnglish && !url.isEmpty() && foundExactEnSub.isEmpty()) {
                                foundExactEnSub = url;
                            } else if (isEnglish && !url.isEmpty() && foundAnyEnSub.isEmpty()) {
                                foundAnyEnSub = url;
                            }
                            if (foundIdSub.isEmpty() && isIndo && !url.isEmpty()) {
                                foundIdSub = url;
                            }
                            if (foundDefSub.isEmpty() && isDef && !isArabic && !url.isEmpty()) {
                                foundDefSub = url;
                            }
                            if (foundNonArSub.isEmpty() && !isArabic && !url.isEmpty()) {
                                foundNonArSub = url;
                            }
                        }
                    }

                    if (!foundExactEnSub.isEmpty()) {
                        foundEnSub = foundExactEnSub;
                    } else if (!foundAnyEnSub.isEmpty()) {
                        foundEnSub = foundAnyEnSub;
                    }

                    // Backend juga menyediakan resolved default sub di data.optString("sub")
                    String backendSub = data.optString("sub", "");
                    String backendSubLang = data.optString("sub_lang", "").toLowerCase();
                    boolean backendIsArabic = backendSubLang.contains("arab") || backendSubLang.equals("ar");

                    if (foundEnSub.isEmpty()) {
                        if (!backendSub.isEmpty() && !backendIsArabic) {
                            foundEnSub = backendSub;
                        } else if (!foundDefSub.isEmpty()) {
                            foundEnSub = foundDefSub;
                        } else if (!foundNonArSub.isEmpty()) {
                            foundEnSub = foundNonArSub;
                        } else if (!subtitleTracks.isEmpty()) {
                            foundEnSub = subtitleTracks.get(0).optString("url", "");
                        }
                    }

                    enSourceSubUrl = foundEnSub;
                    idNativeSubUrl = foundIdSub;

                    // Tentukan activeSubUrl berdasarkan preferensi engine saat ini
                    if ("id".equals(activeSubLang) && "raw".equals(activeEngine) && !idNativeSubUrl.isEmpty()) {
                        activeSubUrl = idNativeSubUrl;
                    } else if ("en".equals(activeSubLang) && "raw".equals(activeEngine)) {
                        activeSubUrl = enSourceSubUrl;
                    } else {
                        // Terjemahan (AIGTX, AI, GTX) menggunakan enSourceSubUrl sebagai sumber terjemahan
                        activeSubUrl = !enSourceSubUrl.isEmpty() ? enSourceSubUrl : (foundNonArSub.isEmpty() ? foundEnSub : foundNonArSub);
                    }

                    rawStreamUrl = streamUrl;
                    streamReferer = referer;
                    masterStreamUrl = (!masterUrl.isEmpty() && isHlsStream(masterUrl)) ? masterUrl : "";

                    JSONObject introObj = data.optJSONObject("intro");
                    if (introObj != null) {
                        long s = (long) (introObj.optDouble("start", 0) * 1000);
                        long e = (long) (introObj.optDouble("end", 0) * 1000);
                        if (e > s && e > 0 && (e - s) >= 5000) {
                            introStartMs = s;
                            introEndMs = e;
                        } else {
                            introStartMs = 0;
                            introEndMs = 0;
                        }
                    } else {
                        introStartMs = 0;
                        introEndMs = 0;
                    }

                    JSONObject outroObj = data.optJSONObject("outro");
                    if (outroObj != null) {
                        long s = (long) (outroObj.optDouble("start", 0) * 1000);
                        long e = (long) (outroObj.optDouble("end", 0) * 1000);
                        if (e > s && e > 0 && (e - s) >= 5000) {
                            outroStartMs = s;
                            outroEndMs = e;
                        } else {
                            outroStartMs = 0;
                            outroEndMs = 0;
                        }
                    } else {
                        outroStartMs = 0;
                        outroEndMs = 0;
                    }
                    currentSkipTargetMs = 0;

                    if (!rawStreamUrl.isEmpty()) {
                        runOnUiThread(() -> {
                            if (resolveId != currentResolveLoadId) return;
                            if (btnQuality != null && activeQuality != null) {
                                btnQuality.setText(activeQuality.toUpperCase());
                            }
                            applyCurrentStream();
                            preResolveNeighbors();
                        });
                    } else {
                        runOnUiThread(() -> {
                            if (resolveId != currentResolveLoadId) return;
                            if (layoutBuffering != null) layoutBuffering.setVisibility(View.GONE);
                            Toast.makeText(this, "URL stream video tidak ditemukan untuk episode ini", Toast.LENGTH_LONG).show();
                        });
                    }
                } else {
                    runOnUiThread(() -> {
                        if (resolveId != currentResolveLoadId) return;
                        if (layoutBuffering != null) layoutBuffering.setVisibility(View.GONE);
                        Toast.makeText(this, "Gagal resolve: " + res.optString("error"), Toast.LENGTH_LONG).show();
                    });
                }
            } catch (Exception e) {
                runOnUiThread(() -> {
                    if (resolveId != currentResolveLoadId) return;
                    String msg = e.getMessage() != null ? e.getMessage() : "";
                    boolean isTimeout = e instanceof java.net.SocketTimeoutException
                            || msg.toLowerCase().contains("time")
                            || msg.toLowerCase().contains("504")
                            || msg.toLowerCase().contains("502");
                    if (isTimeout && consecutiveRecoveryAttempts < MAX_RECOVERY_ATTEMPTS) {
                        consecutiveRecoveryAttempts++;
                        hasAutoRetriedStream = true;
                        if (layoutBuffering != null) {
                            layoutBuffering.setVisibility(View.VISIBLE);
                            if (tvBufferingText != null) {
                                tvBufferingText.setText("MENGHUBUNGKAN ULANG (" + consecutiveRecoveryAttempts + "/" + MAX_RECOVERY_ATTEMPTS + ")...");
                                tvBufferingText.setVisibility(View.VISIBLE);
                            }
                        }
                        Toast.makeText(PlayerActivity.this, "Koneksi stream terputus, mencoba server cadangan...", Toast.LENGTH_SHORT).show();
                        resolveAndPlayStream(resolveId, true);
                        return;
                    }
                    if (layoutBuffering != null) layoutBuffering.setVisibility(View.GONE);
                    Toast.makeText(this, "Error streaming: " + (msg.isEmpty() ? "Koneksi timeout" : msg), Toast.LENGTH_SHORT).show();
                });
            }
        }).start();
    }

    private void applyCurrentStream() {
        if (rawStreamUrl.isEmpty()) return;

        if (layoutBuffering != null) {
            layoutBuffering.setVisibility(View.VISIBLE);
            if (tvBufferingText != null) {
                tvBufferingText.setText("MEMUAT STREAM...");
                tvBufferingText.setVisibility(View.VISIBLE);
            }
        }

        try {
            boolean isHls = isHlsMode || isHlsStream(rawStreamUrl) || isHlsStream(streamReferer);

            String proxiedVideo = "http://127.0.0.1:8767/api/player/video?url=" + Uri.encode(rawStreamUrl)
                    + "&referer=" + Uri.encode(streamReferer);

            Map<String, String> headers = new HashMap<>();
            if (!streamReferer.isEmpty()) {
                headers.put("Referer", streamReferer);
            }

            DefaultHttpDataSource.Factory httpDataSourceFactory = new DefaultHttpDataSource.Factory()
                    .setDefaultRequestProperties(headers)
                    .setAllowCrossProtocolRedirects(true)
                    .setConnectTimeoutMs(15000)
                    .setReadTimeoutMs(30000)
                    .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0");

            String epTitle = (title != null && !title.isEmpty()) ? (title + " - Ep " + ep) : ("Episode " + ep);
            androidx.media3.common.MediaMetadata mediaMetadata = new androidx.media3.common.MediaMetadata.Builder()
                    .setTitle(epTitle)
                    .setDisplayTitle(epTitle)
                    .setArtist(title != null ? title : "")
                    .build();

            MediaItem.Builder mib = new MediaItem.Builder()
                    .setUri(Uri.parse(proxiedVideo))
                    .setMediaMetadata(mediaMetadata);
            hasAppliedTrackSelectionForStream = false;

            if (isHls) {
                mib.setMimeType(MimeTypes.APPLICATION_M3U8);
                HlsMediaSource videoSource = new HlsMediaSource.Factory(httpDataSourceFactory)
                        .setAllowChunklessPreparation(true)
                        .createMediaSource(mib.build());
                player.setMediaSource(videoSource);
            } else {
                androidx.media3.exoplayer.source.ProgressiveMediaSource videoSource =
                        new androidx.media3.exoplayer.source.ProgressiveMediaSource.Factory(httpDataSourceFactory)
                                .createMediaSource(mib.build());
                player.setMediaSource(videoSource);
            }

            if (isHls) {
                applyHlsTrackSelection(activeQuality);
            }

            player.prepare();
            player.play();
            try {
                player.setPlaybackParameters(new PlaybackParameters(currentPlaybackSpeed));
            } catch (Throwable ignored) {}

            applySubtitleSelection();
        } catch (Throwable t) {
            if (layoutBuffering != null) layoutBuffering.setVisibility(View.GONE);
            Toast.makeText(this, "Gagal memutar video: " + t.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private void applySubtitleSelection() {
        applySubtitleSelection(false);
    }

    private void applySubtitleSelection(boolean forceRefresh) {
        updateSubStatusText(false);
        updateExoButtonStates();

        if (!subEnabled || activeSubUrl == null || activeSubUrl.isEmpty()) {
            currentCues = new ArrayList<>();
            runOnUiThread(() -> {
                if (tvSubtitles != null) {
                    tvSubtitles.setText("");
                    tvSubtitles.setVisibility(View.GONE);
                }
            });
            return;
        }

        try {
            if (forceRefresh) {
                currentCues = new ArrayList<>();
            }
            String subModeParam = activeEngine.equals("raw") ? "" : activeEngine;
            String srcParam = activeEngine.equals("raw") ? activeSubLang : "en";

            String effectiveRef = streamReferer != null ? streamReferer : "";
            if (effectiveRef.isEmpty() && activeSubUrl != null) {
                String subLower = activeSubUrl.toLowerCase();
                if (subLower.contains("broforgotsave") || subLower.contains("stellarfrontier") || subLower.contains("megaplay") || subLower.contains("megacloud")) {
                    effectiveRef = "https://megaplay.buzz/";
                }
            }
            String encodedSubUrl = URLEncoder.encode(activeSubUrl, "UTF-8");
            String encodedRef = URLEncoder.encode(effectiveRef, "UTF-8");

            // Jika memilih terjemahan (AIGTX / AI / GTX) dan cues belum dimuat:
            // Unduh dulu subtitle sumber (English/Native) secara instan (0.5s) agar penonton tidak mengalami black screen / tanpa sub.
            if (!subModeParam.isEmpty() && currentCues.isEmpty() && enSourceSubUrl != null && !enSourceSubUrl.isEmpty() && !forceRefresh) {
                String rawSubUrl = "http://127.0.0.1:8767/api/player/sub?url=" + URLEncoder.encode(enSourceSubUrl, "UTF-8")
                        + "&referer=" + encodedRef
                        + "&src=" + URLEncoder.encode(srcParam, "UTF-8")
                        + "&lang=" + URLEncoder.encode(srcParam, "UTF-8");
                loadSubtitlesAsync(rawSubUrl, true);
            }

            // Bangun URL utama untuk terjemahan atau subtitle yang dipilih
            String proxiedSub;
            if (activeSubUrl != null && activeSubUrl.contains("/api/player/sub_custom")) {
                if (subModeParam.isEmpty()) {
                    proxiedSub = activeSubUrl;
                } else {
                    proxiedSub = activeSubUrl + "&lang=" + URLEncoder.encode(activeSubLang, "UTF-8")
                            + "&mode=" + URLEncoder.encode(subModeParam, "UTF-8")
                            + (forceRefresh ? "&refresh=true" : "");
                }
            } else {
                proxiedSub = "http://127.0.0.1:8767/api/player/sub?url=" + encodedSubUrl
                        + "&referer=" + encodedRef
                        + "&src=" + URLEncoder.encode(srcParam, "UTF-8")
                        + "&lang=" + URLEncoder.encode(activeSubLang, "UTF-8")
                        + (subModeParam.isEmpty() ? "" : "&mode=" + URLEncoder.encode(subModeParam, "UTF-8"))
                        + (forceRefresh ? "&refresh=true" : "");
            }

            loadSubtitlesAsync(proxiedSub, false);
        } catch (Exception e) {
            updateSubStatusText(false);
            if (tvSubStatus != null) {
                tvSubStatus.setText("Sub: Gagal (" + e.getMessage() + ")");
            }
        }
    }

    private void loadSubtitlesAsync(String subUrl, boolean isImmediateFallback) {
        final int loadId = ++currentSubLoadId;
        new Thread(() -> {
            HttpURLConnection conn = null;
            try {
                conn = (HttpURLConnection) new URL(subUrl).openConnection();
                conn.setConnectTimeout(15000);
                // Beri waktu cukup (80 detik) bila translasi baru pertama kali dijalankan
                conn.setReadTimeout(isImmediateFallback ? 12000 : 80000);
                conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0");
                conn.setInstanceFollowRedirects(true);

                int respCode = conn.getResponseCode();
                if (respCode >= 400) {
                    throw new Exception("HTTP " + respCode);
                }

                String trTier = conn.getHeaderField("X-Translate-Tier");
                String trErr = conn.getHeaderField("X-Translate-Error");

                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line).append("\n");
                }
                reader.close();

                if (loadId != currentSubLoadId && !isImmediateFallback) return; // Stale request

                List<SubtitleCue> cues = parseVtt(sb.toString());
                if (!cues.isEmpty()) {
                    if (isImmediateFallback) {
                        // Jangan timpa cues terjemahan jika cues utama sudah terisi
                        if (currentCues.isEmpty()) {
                            currentCues = cues;
                            runOnUiThread(() -> subtitleSyncRunnable.run());
                        }
                    } else {
                        currentCues = cues;
                        runOnUiThread(() -> {
                            boolean isFallbackTier = "source".equalsIgnoreCase(trTier) || "source-fallback".equalsIgnoreCase(trTier);
                            if (isFallbackTier) {
                                if (tvSubStatus != null) {
                                    tvSubStatus.setText("Sub: " + activeSubLang.toUpperCase() + " [Terjemahan Gagal, Teks Asli]");
                                }
                            } else {
                                updateSubStatusText(true);
                            }
                            subtitleSyncRunnable.run();
                        });
                    }
                }
            } catch (Exception e) {
                if (!isImmediateFallback && loadId == currentSubLoadId) {
                    runOnUiThread(() -> {
                        // Jika sudah ada cues (misal dari immediate source), jangan kosongkan layar!
                        if (!currentCues.isEmpty()) {
                            tvSubStatus.setText("Sub: " + activeSubLang.toUpperCase() + " [Menggunakan teks asli]");
                        } else {
                            updateSubStatusText(false);
                            if (tvSubStatus != null) {
                                tvSubStatus.setText("Sub: Gagal (" + e.getMessage() + ")");
                            }
                        }
                    });
                }
            } finally {
                if (conn != null) {
                    conn.disconnect();
                }
            }
        }).start();
    }

    private void updateSubStatusText(boolean isLoaded) {
        if (tvSubStatus == null) return;
        if (!subEnabled || activeSubUrl == null || activeSubUrl.isEmpty()) {
            if ("dub".equalsIgnoreCase(activeStreamMode) || (activeSubUrl == null || activeSubUrl.isEmpty())) {
                tvSubStatus.setText("Audio: English Dub (Tanpa Subtitle)");
            } else {
                tvSubStatus.setText("Subtitle: Nonaktif");
            }
            return;
        }
        String engineLabel = "Google GTX (Cepat)";
        if ("gtx+".equals(activeEngine) || "aigtx".equals(activeEngine)) engineLabel = "GTX+ (Smart Fansub & Scene Detection)";
        else if ("ai".equals(activeEngine)) engineLabel = "AI Fansub (" + configuredAiModel + ")";
        else if ("raw".equals(activeEngine)) {
            if ("en".equals(activeSubLang)) engineLabel = "Source English";
            else if ("id".equals(activeSubLang)) engineLabel = "Asli / Resmi";
            else engineLabel = "Source Asli";
        }

        String suffix = isLoaded ? "" : " [Memuat...]";
        tvSubStatus.setText("Sub: " + activeSubLang.toUpperCase() + " • " + engineLabel + suffix);
    }

    private static long parseTimestamp(String token) {
        if (token == null) return -1;
        token = token.trim();
        // Hapus WebVTT settings di baris waktu (misal align:start position:0%)
        int spaceIdx = -1;
        for (int i = 0; i < token.length(); i++) {
            char c = token.charAt(i);
            if (c == ' ' || c == '\t') {
                spaceIdx = i;
                break;
            }
        }
        if (spaceIdx != -1) {
            token = token.substring(0, spaceIdx).trim();
        }
        token = token.replace(',', '.');
        String[] parts = token.split(":");
        try {
            if (parts.length == 3) {
                long h = Long.parseLong(parts[0].trim());
                long m = Long.parseLong(parts[1].trim());
                double s = Double.parseDouble(parts[2].trim());
                return (long) ((h * 3600 + m * 60 + s) * 1000);
            } else if (parts.length == 2) {
                long m = Long.parseLong(parts[0].trim());
                double s = Double.parseDouble(parts[1].trim());
                return (long) ((m * 60 + s) * 1000);
            }
        } catch (Exception ignored) {}
        return -1;
    }

    private List<SubtitleCue> parseVtt(String content) {
        List<SubtitleCue> list = new ArrayList<>();
        if (content == null || content.isEmpty()) return list;

        // Buang BOM jika ada
        if (content.startsWith("\uFEFF")) {
            content = content.substring(1);
        }

        String[] lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n");
        long curStart = -1;
        long curEnd = -1;
        StringBuilder curText = new StringBuilder();

        for (String rawLine : lines) {
            String line = rawLine.trim();

            if (line.contains("-->")) {
                // Simpan cue sebelumnya jika belum sempat ter-flush
                if (curStart != -1 && curEnd != -1 && curText.length() > 0) {
                    String cleaned = curText.toString().replaceAll("<[^>]*>", "").trim();
                    if (!cleaned.isEmpty()) {
                        list.add(new SubtitleCue(curStart, curEnd, cleaned));
                    }
                    curText.setLength(0);
                }

                String[] timeParts = line.split("-->");
                if (timeParts.length >= 2) {
                    curStart = parseTimestamp(timeParts[0]);
                    curEnd = parseTimestamp(timeParts[1]);
                }
            } else if (line.isEmpty()) {
                if (curStart != -1 && curEnd != -1 && curText.length() > 0) {
                    String cleaned = curText.toString().replaceAll("<[^>]*>", "").trim();
                    if (!cleaned.isEmpty()) {
                        list.add(new SubtitleCue(curStart, curEnd, cleaned));
                    }
                }
                curStart = -1;
                curEnd = -1;
                curText.setLength(0);
            } else if (curStart != -1 && curEnd != -1) {
                // Abaikan header atau komentar WebVTT
                if (!line.startsWith("NOTE") && !line.startsWith("STYLE") && !line.startsWith("REGION")) {
                    if (curText.length() > 0) curText.append("\n");
                    curText.append(line);
                }
            }
        }

        if (curStart != -1 && curEnd != -1 && curText.length() > 0) {
            String cleaned = curText.toString().replaceAll("<[^>]*>", "").trim();
            if (!cleaned.isEmpty()) {
                list.add(new SubtitleCue(curStart, curEnd, cleaned));
            }
        }
        return list;
    }

    private SubtitleCue findActiveCue(long posMs) {
        List<SubtitleCue> cues = currentCues;
        if (cues == null || cues.isEmpty()) return null;
        int low = 0;
        int high = cues.size() - 1;
        int best = -1;
        while (low <= high) {
            int mid = (low + high) >>> 1;
            SubtitleCue cue = cues.get(mid);
            if (cue.startMs <= posMs) {
                best = mid;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        if (best != -1) {
            SubtitleCue c = cues.get(best);
            if (posMs <= c.endMs) return c;
        }
        return null;
    }

    private void showSpeedSelectorDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
        builder.setTitle("Kecepatan Putar Video");

        int checkedItem = 2; // Default 1.0x (index 2)
        for (int i = 0; i < PLAYBACK_SPEEDS.length; i++) {
            if (Math.abs(PLAYBACK_SPEEDS[i] - currentPlaybackSpeed) < 0.05f) {
                checkedItem = i;
                break;
            }
        }

        builder.setSingleChoiceItems(PLAYBACK_SPEED_LABELS, checkedItem, (dialog, which) -> {
            if (which >= 0 && which < PLAYBACK_SPEEDS.length) {
                applyPlaybackSpeed(PLAYBACK_SPEEDS[which]);
            }
            dialog.dismiss();
        });

        builder.setNegativeButton("Batal", (dialog, which) -> dialog.dismiss());
        builder.setOnDismissListener(dialog -> {
            if (playerView != null) {
                playerView.showController();
                if (btnSpeed != null && btnSpeed.getVisibility() == View.VISIBLE) {
                    btnSpeed.requestFocus();
                } else if (btnExoSettings != null && btnExoSettings.getVisibility() == View.VISIBLE) {
                    btnExoSettings.requestFocus();
                }
            }
        });
        builder.show();
    }

    private void applyPlaybackSpeed(float speed) {
        currentPlaybackSpeed = speed;
        if (player != null) {
            try {
                player.setPlaybackParameters(new PlaybackParameters(currentPlaybackSpeed));
            } catch (Throwable ignored) {}
        }
        updateSpeedButtonLabel();
        Toast.makeText(this, "Kecepatan: " + formatSpeedLabel(speed), Toast.LENGTH_SHORT).show();
    }

    private void updateSpeedButtonLabel() {
        String label = formatSpeedLabel(currentPlaybackSpeed);
        if (btnSpeed != null) {
            btnSpeed.setText(label);
        }
        if (btnPortraitSpeed != null) {
            btnPortraitSpeed.setText(label);
        }
    }

    private String formatSpeedLabel(float speed) {
        if (speed == 1.0f) return "1.0x";
        if (speed == 0.5f) return "0.5x";
        if (speed == 0.75f) return "0.75x";
        if (speed == 1.25f) return "1.25x";
        if (speed == 1.5f) return "1.5x";
        if (speed == 1.75f) return "1.75x";
        if (speed == 2.0f) return "2.0x";
        return String.format(java.util.Locale.US, "%.2fx", speed);
    }

    private void showQualitySelectorDialog() {
        if (streamVariants.isEmpty()) {
            Toast.makeText(this, "Hanya satu kualitas resolusi tersedia untuk video ini", Toast.LENGTH_SHORT).show();
            return;
        }
        AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
        builder.setTitle("Pilih Resolusi Video");

        List<String> options = new ArrayList<>();
        int selectedIdx = 0;
        for (int i = 0; i < streamVariants.size(); i++) {
            JSONObject v = streamVariants.get(i);
            String q = v.optString("q", "auto");
            boolean isCurrent = q.equalsIgnoreCase(activeQuality)
                    || (rawStreamUrl.equals(v.optString("url", "")) && !rawStreamUrl.isEmpty());
            if (isCurrent) selectedIdx = i;
            options.add(q.toUpperCase() + (isCurrent ? " [Aktif]" : ""));
        }

        builder.setSingleChoiceItems(options.toArray(new String[0]), selectedIdx, (dialog, which) -> {
            if (which >= 0 && which < streamVariants.size()) {
                JSONObject picked = streamVariants.get(which);
                String newQ = picked.optString("q", "auto");
                String newUrl = picked.optString("url", "");
                dialog.dismiss();
                switchQuality(newQ, newUrl);
            }
        });

        builder.setNegativeButton("Batal", (dialog, which) -> dialog.dismiss());
        builder.setOnDismissListener(dialog -> {
            if (playerView != null) {
                playerView.showController();
                if (btnQuality != null && btnQuality.getVisibility() == View.VISIBLE) {
                    btnQuality.requestFocus();
                } else if (btnExoSettings != null && btnExoSettings.getVisibility() == View.VISIBLE) {
                    btnExoSettings.requestFocus();
                }
            }
        });
        builder.show();
    }

    private void switchQuality(String newQ, String newUrl) {
        if (newQ == null || newQ.isEmpty()) return;
        activeQuality = newQ;
        if (btnQuality != null) {
            btnQuality.setText(newQ.toUpperCase());
        }
        getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE)
                .edit().putString("pref_quality", newQ).apply();

        hasFallbackAttempted = false;
        Toast.makeText(this, "Mengubah resolusi ke " + newQ.toUpperCase(), Toast.LENGTH_SHORT).show();

        boolean isHls = isHlsMode || isHlsStream(rawStreamUrl) || isHlsStream(masterStreamUrl);

        if (isHls && player != null) {
            long resumePos = player.getCurrentPosition();
            boolean wasPlaying = player.isPlaying();

            hasAppliedTrackSelectionForStream = true;
            applyHlsTrackSelection(newQ);

            // Khusus Android TV: True Seamless Quality Switching
            // Tidak memanggil player.stop() atau player.prepare() agar pemutaran tidak terputus (tanpa black screen/spinner).
            // SurfaceView dan hardware decoder otomatis menyesuaikan dimensi buffer pada batas segmen/GOP berikutnya.
            if (TvFocusHelper.isTv(this)) {
                if (playerView != null) {
                    playerView.setResizeMode(currentResizeMode);
                    View sv = playerView.getVideoSurfaceView();
                    if (sv != null) {
                        sv.requestLayout();
                    }
                    playerView.requestLayout();
                }
                return;
            }

            // Pada Android Mobile: Pertahankan alokasi/perilaku bawaan yang ada (100% UNTOUCHED)
            player.stop();
            if (resumePos > 0) {
                player.seekTo(resumePos);
            }
            player.prepare();
            if (wasPlaying) {
                player.play();
            }

            if (playerView != null) {
                playerView.setResizeMode(currentResizeMode);
                View sv = playerView.getVideoSurfaceView();
                if (sv != null) {
                    sv.requestLayout();
                }
                playerView.requestLayout();
            }
            return;
        }

        // Jalur non-HLS (Progressive MP4 tunggal): reload stream dengan URL baru
        if (newUrl == null || newUrl.isEmpty() || newUrl.equals(rawStreamUrl)) return;
        long resumePos = player != null ? player.getCurrentPosition() : 0;
        boolean wasPlaying = player != null && player.isPlaying();

        rawStreamUrl = newUrl;
        isHlsMode = isHlsStream(newUrl);

        applyCurrentStream();

        if (player != null) {
            androidx.media3.common.TrackSelectionParameters params = player.getTrackSelectionParameters().buildUpon()
                    .clearVideoSizeConstraints()
                    .clearOverridesOfType(androidx.media3.common.C.TRACK_TYPE_VIDEO)
                    .build();
            player.setTrackSelectionParameters(params);

            if (resumePos > 0) {
                player.seekTo(resumePos);
                if (wasPlaying) {
                    player.play();
                }
            }
        }

        if (playerView != null) {
            playerView.setResizeMode(currentResizeMode);
            View sv = playerView.getVideoSurfaceView();
            if (sv != null) {
                sv.requestLayout();
            }
            playerView.requestLayout();
        }
    }

    private void applyHlsTrackSelection(String quality) {
        if (player == null) return;
        if (quality == null || quality.isEmpty()) quality = "best";

        androidx.media3.common.TrackSelectionParameters.Builder builder =
                player.getTrackSelectionParameters().buildUpon()
                        .clearOverridesOfType(androidx.media3.common.C.TRACK_TYPE_VIDEO)
                        .clearVideoSizeConstraints();

        if (!"auto".equalsIgnoreCase(quality)) {
            int targetH = 1080;
            if ("best".equalsIgnoreCase(quality) || "hd".equalsIgnoreCase(quality) || quality.contains("1080")) {
                targetH = 1080;
            } else if (quality.contains("720")) {
                targetH = 720;
            } else if (quality.contains("480")) {
                targetH = 480;
            } else if (quality.contains("360")) {
                targetH = 360;
            }

            androidx.media3.common.Tracks currentTracks = player.getCurrentTracks();
            androidx.media3.common.TrackGroup targetGroup = null;
            int targetIndex = -1;
            int bestDiff = Integer.MAX_VALUE;

            for (androidx.media3.common.Tracks.Group group : currentTracks.getGroups()) {
                if (group.getType() == androidx.media3.common.C.TRACK_TYPE_VIDEO) {
                    androidx.media3.common.TrackGroup tg = group.getMediaTrackGroup();
                    for (int i = 0; i < tg.length; i++) {
                        androidx.media3.common.Format format = tg.getFormat(i);
                        int diff = Math.abs(format.height - targetH);
                        if (diff < bestDiff) {
                            bestDiff = diff;
                            targetGroup = tg;
                            targetIndex = i;
                        }
                    }
                }
            }

            if (targetGroup != null && targetIndex != -1) {
                builder.addOverride(new androidx.media3.common.TrackSelectionOverride(targetGroup, targetIndex));
            } else {
                int maxH = Integer.MAX_VALUE;
                int maxW = Integer.MAX_VALUE;
                if ("best".equalsIgnoreCase(quality) || "hd".equalsIgnoreCase(quality) || quality.contains("1080")) {
                    maxH = 1080; maxW = 1920;
                } else if (quality.contains("720")) {
                    maxH = 720; maxW = 1280;
                } else if (quality.contains("480")) {
                    maxH = 480; maxW = 854;
                } else if (quality.contains("360")) {
                    maxH = 360; maxW = 640;
                }

                builder.setMaxVideoSize(maxW, maxH);
            }
        }

        androidx.media3.common.TrackSelectionParameters newParams = builder.build();
        if (!newParams.equals(player.getTrackSelectionParameters())) {
            player.setTrackSelectionParameters(newParams);
        }
    }

    private void showSubtitleSelectorDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
        builder.setTitle("Pengaturan Subtitle & Mesin Terjemahan");

        List<String> options = new ArrayList<>();
        List<Runnable> actions = new ArrayList<>();

        if (enSourceSubUrl.isEmpty() && subtitleTracks.isEmpty() && customSubtitleName.isEmpty()) {
            String msg = "dub".equalsIgnoreCase(activeStreamMode) ? "Audio: English Dub (Tidak ada file subtitle bawaan)" : "Tidak ada file subtitle bawaan untuk video ini";
            options.add("[Info] " + msg);
            actions.add(() -> {});
        } else {
            // 0. Subtitle Kustom yang pernah dimuat
            if (!customSubtitleName.isEmpty()) {
                boolean isCustomSelected = subEnabled && "custom".equals(activeSubLang);
                options.add("[Kustom] " + customSubtitleName + (isCustomSelected ? " [Aktif]" : ""));
                actions.add(() -> {
                    subEnabled = true;
                    activeSubLang = "custom";
                    activeEngine = "raw";
                    if (!customSubtitleUrl.isEmpty()) {
                        activeSubUrl = customSubtitleUrl;
                    }
                });
            }

            // 1. Google GTX Murni (Prioritas Pertama / Super Cepat)
            if (!enSourceSubUrl.isEmpty()) {
                boolean isGtxSelected = subEnabled && "id".equals(activeSubLang) && "gtx".equals(activeEngine);
                options.add("[ID] Bahasa Indonesia (Google GTX Murni - Cepat)" + (isGtxSelected ? " [Aktif]" : ""));
                actions.add(() -> {
                    subEnabled = true;
                    activeSubLang = "id";
                    activeEngine = "gtx";
                    activeSubUrl = enSourceSubUrl;
                });

                // 2. GTX+ (Prioritas Kedua / GTX + Smart Fansub & Scene Detection)
                boolean isGtxPlusSelected = subEnabled && "id".equals(activeSubLang) && ("gtx+".equals(activeEngine) || "aigtx".equals(activeEngine));
                options.add("[ID] Bahasa Indonesia (GTX+ - Smart Fansub & Scene Detection)" + (isGtxPlusSelected ? " [Aktif]" : ""));
                actions.add(() -> {
                    subEnabled = true;
                    activeSubLang = "id";
                    activeEngine = "gtx+";
                    activeSubUrl = enSourceSubUrl;
                });

                // 3. AI Fansub (Prioritas Ketiga / LLM Translate)
                boolean isAiSelected = subEnabled && "id".equals(activeSubLang) && "ai".equals(activeEngine);
                String aiOptionText = "[AI] Bahasa Indonesia (AI Fansub / " + configuredAiModel + ")"
                        + (hasAiKey ? " [SIAP]" : " [Butuh Key]")
                        + (isAiSelected ? " [Aktif]" : "");
                options.add(aiOptionText);
                actions.add(() -> {
                    subEnabled = true;
                    activeSubLang = "id";
                    activeEngine = "ai";
                    activeSubUrl = enSourceSubUrl;
                    if (!hasAiKey) {
                        Toast.makeText(this, "Perhatian: API Key AI belum disetel (:apikey <key> di home). Menggunakan GTX sebagai fallback otomatis.", Toast.LENGTH_LONG).show();
                    }
                });
            }

            // 4. Native Indonesian (jika tersedia di track asli)
            if (!idNativeSubUrl.isEmpty()) {
                boolean isIdNativeSelected = subEnabled && "id".equals(activeSubLang) && "raw".equals(activeEngine) && idNativeSubUrl.equals(activeSubUrl);
                options.add("[ID] Bahasa Indonesia (Asli / Bawaan)" + (isIdNativeSelected ? " [Aktif]" : ""));
                actions.add(() -> {
                    subEnabled = true;
                    activeSubLang = "id";
                    activeEngine = "raw";
                    activeSubUrl = idNativeSubUrl;
                });
            }

            // 5. English (Original)
            if (!enSourceSubUrl.isEmpty() && !enSourceSubUrl.equals(customSubtitleUrl)) {
                boolean isEnSelected = subEnabled && "en".equals(activeSubLang) && "raw".equals(activeEngine);
                options.add("[EN] English (Original / Asli)" + (isEnSelected ? " [Aktif]" : ""));
                actions.add(() -> {
                    subEnabled = true;
                    activeSubLang = "en";
                    activeEngine = "raw";
                    activeSubUrl = enSourceSubUrl;
                });
            }

            // 6. Daftar track bahasa lain yang tersedia (misal Spanish, French, Japanese, dsb.)
            for (int i = 0; i < subtitleTracks.size(); i++) {
                JSONObject s = subtitleTracks.get(i);
                String url = s.optString("url", "");
                String lbl = s.optString("label", "Track " + (i + 1));
                String lang = s.optString("lang", "").toLowerCase();
                // Lewati track English & ID native karena sudah disediakan di menu utama di atas
                if (url.equals(enSourceSubUrl) || url.equals(idNativeSubUrl) || url.equals(customSubtitleUrl)) {
                    continue;
                }
                boolean isThisSelected = subEnabled && "raw".equals(activeEngine) && url.equals(activeSubUrl);
                options.add(lbl + (isThisSelected ? " [Aktif]" : ""));
                actions.add(() -> {
                    subEnabled = true;
                    activeSubLang = lang.isEmpty() ? "en" : lang;
                    activeEngine = "raw";
                    activeSubUrl = url;
                });
            }
        }

        // Opsi Muat Ulang / Terjemahkan Ulang Subtitle (Hapus Cache)
        if (subEnabled && !"raw".equals(activeEngine)) {
            options.add("[Refresh] Terjemahkan Ulang Subtitle (Hapus Cache)");
            actions.add(() -> {
                Toast.makeText(this, "Menerjemahkan ulang subtitle dari awal...", Toast.LENGTH_SHORT).show();
                applySubtitleSelection(true);
            });
        }

        // Opsi Subtitle Kustom (File Lokal / URL)
        options.add("[+] Pilih File Subtitle Lokal (.srt / .vtt)...");
        actions.add(this::openSubtitleFilePicker);

        options.add("[+] Masukkan URL Subtitle Kustom...");
        actions.add(this::showCustomSubtitleUrlDialog);

        // 7. Pengaturan Tampilan & Gaya Subtitle
        options.add("Pengaturan Tampilan (Posisi, Latar Belakang & Ukuran)...");
        actions.add(this::showSubtitleStyleDialog);

        // 8. Matikan Subtitle
        options.add("Matikan Subtitle" + (!subEnabled ? " [Aktif]" : ""));
        actions.add(() -> {
            subEnabled = false;
        });

        builder.setItems(options.toArray(new String[0]), (dialog, which) -> {
            if (which >= 0 && which < actions.size()) {
                String chosen = options.get(which);
                actions.get(which).run();
                if (!chosen.contains("[Refresh]") && !chosen.contains("[+]")) {
                    getSharedPreferences("tatap_player_prefs", MODE_PRIVATE).edit()
                            .putString("pref_sub_engine", activeEngine)
                            .putString("pref_sub_lang", activeSubLang)
                            .putBoolean("pref_sub_enabled", subEnabled)
                            .apply();
                    applySubtitleSelection();
                    Toast.makeText(this, "Subtitle diperbarui: " + (subEnabled ? activeSubLang.toUpperCase() + " [" + activeEngine + "]" : "OFF"), Toast.LENGTH_SHORT).show();
                }
            }
        });

        builder.setNegativeButton("Tutup", (dialog, which) -> dialog.dismiss());
        builder.setOnDismissListener(dialog -> {
            if (playerView != null) {
                playerView.showController();
                if (btnSubSelector != null && btnSubSelector.getVisibility() == View.VISIBLE) {
                    btnSubSelector.requestFocus();
                } else if (btnExoSub != null && btnExoSub.getVisibility() == View.VISIBLE) {
                    btnExoSub.requestFocus();
                }
            }
        });
        builder.show();
    }

    private void openSubtitleFilePicker() {
        try {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType("*/*");
            String[] mimeTypes = {"text/plain", "text/vtt", "application/x-subrip", "application/octet-stream"};
            intent.putExtra(Intent.EXTRA_MIME_TYPES, mimeTypes);
            startActivityForResult(intent, REQUEST_CODE_PICK_SUBTITLE);
        } catch (Exception e) {
            try {
                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.setType("*/*");
                startActivityForResult(intent, REQUEST_CODE_PICK_SUBTITLE);
            } catch (Exception ex) {
                Toast.makeText(this, "Gagal membuka pengelola berkas: " + ex.getMessage(), Toast.LENGTH_SHORT).show();
            }
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_CODE_PICK_SUBTITLE && resultCode == RESULT_OK && data != null && data.getData() != null) {
            Uri uri = data.getData();
            loadCustomSubtitleFromUri(uri);
        }
    }

    private void loadCustomSubtitleFromUri(Uri uri) {
        new Thread(() -> {
            try {
                InputStream is = getContentResolver().openInputStream(uri);
                if (is == null) {
                    runOnUiThread(() -> Toast.makeText(this, "Tidak dapat membaca file subtitle", Toast.LENGTH_SHORT).show());
                    return;
                }
                BufferedReader reader = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line).append("\n");
                }
                reader.close();
                is.close();
                String rawSub = sb.toString();

                String displayName = "File Lokal";
                try (android.database.Cursor cursor = getContentResolver().query(uri, null, null, null, null)) {
                    if (cursor != null && cursor.moveToFirst()) {
                        int nameIdx = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME);
                        if (nameIdx >= 0) {
                            String name = cursor.getString(nameIdx);
                            if (name != null && !name.isEmpty()) displayName = name;
                        }
                    }
                } catch (Exception ignored) {}

                final String finalName = displayName;
                String customUrl = registerCustomSubtitleToBackend(rawSub, finalName);
                List<SubtitleCue> cues = parseVtt(rawSub);

                runOnUiThread(() -> {
                    if (cues.isEmpty()) {
                        Toast.makeText(this, "Subtitle kosong atau format tidak dikenali (.srt/.vtt)", Toast.LENGTH_SHORT).show();
                        return;
                    }
                    customSubtitleName = finalName;
                    customSubtitleUrl = customUrl != null ? customUrl : "";
                    currentCues = cues;
                    subEnabled = true;
                    activeSubLang = "custom";
                    activeEngine = "raw";
                    if (!customSubtitleUrl.isEmpty()) {
                        activeSubUrl = customSubtitleUrl;
                        enSourceSubUrl = customSubtitleUrl;
                    }
                    if (tvSubtitles != null) {
                        tvSubtitles.setText("");
                        tvSubtitles.setVisibility(View.GONE);
                    }
                    updateSubStatusText(true);
                    subtitleSyncRunnable.run();
                    Toast.makeText(this, "Subtitle aktif: " + cues.size() + " cue (" + finalName + ")", Toast.LENGTH_SHORT).show();
                });
            } catch (Exception e) {
                runOnUiThread(() -> Toast.makeText(this, "Gagal memuat subtitle: " + e.getMessage(), Toast.LENGTH_SHORT).show());
            }
        }).start();
    }

    private String registerCustomSubtitleToBackend(String text, String filename) {
        HttpURLConnection conn = null;
        try {
            URL u = new URL("http://127.0.0.1:8767/api/player/sub_custom");
            conn = (HttpURLConnection) u.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setDoOutput(true);
            conn.setConnectTimeout(6000);
            conn.setReadTimeout(6000);
            JSONObject json = new JSONObject();
            json.put("text", text);
            json.put("filename", filename);
            json.put("lang", "en");
            byte[] bytes = json.toString().getBytes(StandardCharsets.UTF_8);
            try (OutputStream os = conn.getOutputStream()) {
                os.write(bytes);
            }
            if (conn.getResponseCode() == 200) {
                BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
                StringBuilder resp = new StringBuilder();
                String l;
                while ((l = br.readLine()) != null) resp.append(l);
                br.close();
                JSONObject r = new JSONObject(resp.toString());
                if (r.optBoolean("success", false)) {
                    JSONObject d = r.optJSONObject("data");
                    if (d != null) {
                        String relUrl = d.optString("url", "");
                        if (!relUrl.isEmpty()) {
                            return "http://127.0.0.1:8767" + relUrl;
                        }
                    }
                }
            }
        } catch (Exception ignored) {
        } finally {
            if (conn != null) conn.disconnect();
        }
        return null;
    }

    private void showCustomSubtitleUrlDialog() {
        AlertDialog.Builder b = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
        b.setTitle("Masukkan URL Subtitle");
        final EditText input = new EditText(this);
        input.setHint("https://example.com/sub.vtt atau .srt");
        input.setTextColor(0xFFFFFFFF);
        input.setHintTextColor(0xFF888888);
        input.setSingleLine(true);
        input.setPadding(40, 30, 40, 30);
        b.setView(input);

        b.setPositiveButton("Muat", (dialog, which) -> {
            String url = input.getText().toString().trim();
            if (url.isEmpty()) {
                Toast.makeText(this, "URL subtitle tidak boleh kosong", Toast.LENGTH_SHORT).show();
                return;
            }
            loadCustomSubtitleFromUrl(url);
        });
        b.setNegativeButton("Batal", (dialog, which) -> dialog.dismiss());
        AlertDialog dialog = b.create();
        dialog.show();
    }

    private void loadCustomSubtitleFromUrl(String url) {
        Toast.makeText(this, "Mengunduh subtitle dari URL...", Toast.LENGTH_SHORT).show();
        new Thread(() -> {
            HttpURLConnection conn = null;
            try {
                URL u = new URL("http://127.0.0.1:8767/api/player/sub_custom");
                conn = (HttpURLConnection) u.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                conn.setDoOutput(true);
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(15000);
                JSONObject json = new JSONObject();
                json.put("url", url);
                json.put("filename", "Kustom URL");
                byte[] bytes = json.toString().getBytes(StandardCharsets.UTF_8);
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(bytes);
                }
                int respCode = conn.getResponseCode();
                if (respCode == 200) {
                    BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
                    StringBuilder resp = new StringBuilder();
                    String l;
                    while ((l = br.readLine()) != null) resp.append(l);
                    br.close();
                    JSONObject r = new JSONObject(resp.toString());
                    if (r.optBoolean("success", false)) {
                        JSONObject d = r.optJSONObject("data");
                        if (d != null) {
                            String relUrl = d.optString("url", "");
                            String subFullUrl = "http://127.0.0.1:8767" + relUrl;
                            runOnUiThread(() -> {
                                customSubtitleName = "URL: " + (url.length() > 30 ? url.substring(0, 27) + "..." : url);
                                customSubtitleUrl = subFullUrl;
                                activeSubUrl = subFullUrl;
                                enSourceSubUrl = subFullUrl;
                                activeSubLang = "custom";
                                activeEngine = "raw";
                                subEnabled = true;
                                applySubtitleSelection();
                                Toast.makeText(this, "Subtitle dari URL berhasil diaktifkan", Toast.LENGTH_SHORT).show();
                            });
                            return;
                        }
                    }
                    String err = r.optString("error", "Format tidak valid");
                    runOnUiThread(() -> Toast.makeText(this, "Gagal memuat subtitle: " + err, Toast.LENGTH_LONG).show());
                } else {
                    runOnUiThread(() -> Toast.makeText(this, "Server error: HTTP " + respCode, Toast.LENGTH_SHORT).show());
                }
            } catch (Exception e) {
                runOnUiThread(() -> Toast.makeText(this, "Koneksi gagal: " + e.getMessage(), Toast.LENGTH_LONG).show());
            } finally {
                if (conn != null) conn.disconnect();
            }
        }).start();
    }

    private void applySubtitleStyle() {
        if (tvSubtitles == null) return;
        SharedPreferences sp = getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
        boolean isTv = TvFocusHelper.isTv(this);
        String pos = sp.getString("sub_pos", "low");
        String bg = sp.getString("sub_bg", "subtle");
        String defaultSize = isTv ? "large" : "medium";
        String size = sp.getString("sub_size", defaultSize);

        // 1. Margin Bawah (Posisi)
        int marginDp = 22; // Default 22dp: Rendah & pas di batas bawah layar
        if ("mid".equals(pos)) marginDp = 36;
        else if ("high".equals(pos)) marginDp = 54;

        int marginPx = (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, marginDp, getResources().getDisplayMetrics());
        ViewGroup.MarginLayoutParams lp = (ViewGroup.MarginLayoutParams) tvSubtitles.getLayoutParams();
        if (lp != null) {
            lp.bottomMargin = marginPx;
            tvSubtitles.setLayoutParams(lp);
        }

        // 2. Ukuran Font & Spasi Baris Dinamis (Adaptif Android TV vs Mobile)
        float sizeSp;
        if (isTv) {
            if ("small".equals(size)) sizeSp = 18f;
            else if ("medium".equals(size)) sizeSp = 22f;
            else if ("large".equals(size)) sizeSp = 26f; // Standar TV
            else if ("xlarge".equals(size)) sizeSp = 30f;
            else if ("xxlarge".equals(size)) sizeSp = 34f; // Jarak Jauh
            else if ("jumbo".equals(size)) sizeSp = 38f;  // Layar Besar
            else if ("max".equals(size)) sizeSp = 42f;    // Maksimal
            else sizeSp = 26f;
        } else {
            if ("small".equals(size)) sizeSp = 14f;
            else if ("medium".equals(size)) sizeSp = 17f; // Standar HP
            else if ("large".equals(size)) sizeSp = 21f;
            else if ("xlarge".equals(size)) sizeSp = 25f;
            else if ("xxlarge".equals(size)) sizeSp = 29f;
            else if ("jumbo".equals(size)) sizeSp = 33f;
            else if ("max".equals(size)) sizeSp = 36f;
            else sizeSp = 17f;
        }
        tvSubtitles.setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp);
        // Spasi baris proporsional agar kalimat multi-baris berukuran besar tidak tumpang tindih
        tvSubtitles.setLineSpacing(0f, isTv ? 1.25f : 1.15f);

        // 3. Latar Belakang & Shadow
        GradientDrawable gd = new GradientDrawable();
        int cornerPx = (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, isTv ? 8 : 6, getResources().getDisplayMetrics());
        gd.setCornerRadius(cornerPx);

        if ("transparent".equals(bg)) {
            // Tanpa box background sama sekali, teks tebal dengan shadow tajam (gaya fansub modern)
            tvSubtitles.setBackground(null);
            tvSubtitles.setShadowLayer(isTv ? 8f : 6f, 2f, 2f, 0xFF000000);
        } else {
            int bgColor = 0x4D000000; // 30% alpha (samar & lembut, tidak pekat)
            if ("medium".equals(bg)) bgColor = 0x8C000000; // 55%
            else if ("dark".equals(bg)) bgColor = 0xCC000000; // 80% pekat
            gd.setColor(bgColor);
            tvSubtitles.setBackground(gd);
            tvSubtitles.setShadowLayer(isTv ? 6f : 4f, 1.5f, 1.5f, 0xFF000000);
        }
    }

    private void showSubtitleStyleDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
        builder.setTitle("Pengaturan Tampilan Subtitle");

        SharedPreferences sp = getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
        boolean isTv = TvFocusHelper.isTv(this);
        String curPos = sp.getString("sub_pos", "low");
        String curBg = sp.getString("sub_bg", "subtle");
        String defaultSize = isTv ? "large" : "medium";
        String curSize = sp.getString("sub_size", defaultSize);

        String posLabel = "low".equals(curPos) ? "Bawah (22dp) [Pas]" : ("mid".equals(curPos) ? "Sedang (36dp)" : "Tinggi (54dp)");
        String bgLabel = "transparent".equals(curBg) ? "Transparan (Tanpa Box)" : ("subtle".equals(curBg) ? "Samar / Lembut (30%)" : ("medium".equals(curBg) ? "Sedang (55%)" : "Pekat (80%)"));

        String sizeLabel;
        if (isTv) {
            if ("small".equals(curSize)) sizeLabel = "Kecil (18sp)";
            else if ("medium".equals(curSize)) sizeLabel = "Sedang (22sp)";
            else if ("large".equals(curSize)) sizeLabel = "Besar (26sp) [Standar TV]";
            else if ("xlarge".equals(curSize)) sizeLabel = "Sangat Besar (30sp)";
            else if ("xxlarge".equals(curSize)) sizeLabel = "Ekstra Besar (34sp) [Jarak Jauh]";
            else if ("jumbo".equals(curSize)) sizeLabel = "Jumbo (38sp) [Layar Besar]";
            else if ("max".equals(curSize)) sizeLabel = "Maksimal (42sp)";
            else sizeLabel = "Besar (26sp)";
        } else {
            if ("small".equals(curSize)) sizeLabel = "Kecil (14sp)";
            else if ("medium".equals(curSize)) sizeLabel = "Sedang (17sp) [Standar HP]";
            else if ("large".equals(curSize)) sizeLabel = "Besar (21sp)";
            else if ("xlarge".equals(curSize)) sizeLabel = "Sangat Besar (25sp)";
            else if ("xxlarge".equals(curSize)) sizeLabel = "Ekstra Besar (29sp)";
            else if ("jumbo".equals(curSize)) sizeLabel = "Jumbo (33sp)";
            else if ("max".equals(curSize)) sizeLabel = "Maksimal (36sp)";
            else sizeLabel = "Sedang (17sp)";
        }

        String[] menu = new String[]{
                "Posisi Subtitle: " + posLabel,
                "Latar Belakang: " + bgLabel,
                "Ukuran Huruf: " + sizeLabel,
                "Reset ke Default"
        };

        builder.setItems(menu, (dialog, which) -> {
            if (which == 0) {
                showPositionPicker(sp);
            } else if (which == 1) {
                showBackgroundPicker(sp);
            } else if (which == 2) {
                showSizePicker(sp);
            } else if (which == 3) {
                sp.edit().putString("sub_pos", "low").putString("sub_bg", "subtle").putString("sub_size", defaultSize).apply();
                applySubtitleStyle();
                Toast.makeText(this, "Tampilan subtitle direset ke default", Toast.LENGTH_SHORT).show();
            }
        });

        builder.setNegativeButton("Tutup", (dialog, which) -> dialog.dismiss());
        builder.setOnDismissListener(dialog -> {
            if (playerView != null) {
                playerView.showController();
                if (btnSubStyle != null && btnSubStyle.getVisibility() == View.VISIBLE) {
                    btnSubStyle.requestFocus();
                } else if (btnExoSettings != null && btnExoSettings.getVisibility() == View.VISIBLE) {
                    btnExoSettings.requestFocus();
                }
            }
        });
        builder.show();
    }

    private void showPositionPicker(SharedPreferences sp) {
        String[] options = new String[]{
                "Bawah / Rendah (22dp) [Direkomendasikan]",
                "Sedang (36dp)",
                "Tinggi (54dp)"
        };
        String cur = sp.getString("sub_pos", "low");
        int checked = "high".equals(cur) ? 2 : ("mid".equals(cur) ? 1 : 0);

        new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert)
                .setTitle("Pilih Posisi Subtitle")
                .setSingleChoiceItems(options, checked, (dialog, which) -> {
                    String val = which == 2 ? "high" : (which == 1 ? "mid" : "low");
                    sp.edit().putString("sub_pos", val).apply();
                    applySubtitleStyle();
                    dialog.dismiss();
                    Toast.makeText(this, "Posisi subtitle disimpan", Toast.LENGTH_SHORT).show();
                })
                .setNegativeButton("Batal", null)
                .show();
    }

    private void showBackgroundPicker(SharedPreferences sp) {
        String[] options = new String[]{
                "Transparan (Tanpa Box / Shadow Teks Bersih)",
                "Samar / Lembut (30% Alpha) [Direkomendasikan]",
                "Sedang (55% Alpha)",
                "Pekat (80% Alpha)"
        };
        String cur = sp.getString("sub_bg", "subtle");
        int checked = "transparent".equals(cur) ? 0 : ("medium".equals(cur) ? 2 : ("dark".equals(cur) ? 3 : 1));

        new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert)
                .setTitle("Pilih Latar Belakang Subtitle")
                .setSingleChoiceItems(options, checked, (dialog, which) -> {
                    String val = which == 0 ? "transparent" : (which == 2 ? "medium" : (which == 3 ? "dark" : "subtle"));
                    sp.edit().putString("sub_bg", val).apply();
                    applySubtitleStyle();
                    dialog.dismiss();
                    Toast.makeText(this, "Gaya latar subtitle disimpan", Toast.LENGTH_SHORT).show();
                })
                .setNegativeButton("Batal", null)
                .show();
    }

    private void showSizePicker(SharedPreferences sp) {
        boolean isTv = TvFocusHelper.isTv(this);
        String defaultSize = isTv ? "large" : "medium";
        String cur = sp.getString("sub_size", defaultSize);

        String[] options;
        String[] values;

        if (isTv) {
            options = new String[]{
                    "Kecil (18sp)",
                    "Sedang (22sp)",
                    "Besar (26sp) [Standar TV]",
                    "Sangat Besar (30sp)",
                    "Ekstra Besar (34sp) [Jarak Jauh 3.5m+]",
                    "Jumbo (38sp) [Layar Besar 55\"-75\"]",
                    "Maksimal (42sp) [Visibilitas Tinggi]"
            };
            values = new String[]{"small", "medium", "large", "xlarge", "xxlarge", "jumbo", "max"};
        } else {
            options = new String[]{
                    "Kecil (14sp)",
                    "Sedang (17sp) [Standar HP]",
                    "Besar (21sp)",
                    "Sangat Besar (25sp)",
                    "Ekstra Besar (29sp)",
                    "Jumbo (33sp)",
                    "Maksimal (36sp)"
            };
            values = new String[]{"small", "medium", "large", "xlarge", "xxlarge", "jumbo", "max"};
        }

        int checked = 2; // Default "large" di TV
        if (!isTv) checked = 1; // Default "medium" di HP
        for (int i = 0; i < values.length; i++) {
            if (values[i].equals(cur)) {
                checked = i;
                break;
            }
        }

        final String[] finalValues = values;
        new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert)
                .setTitle("Pilih Ukuran Huruf Subtitle")
                .setSingleChoiceItems(options, checked, (dialog, which) -> {
                    String val = (which >= 0 && which < finalValues.length) ? finalValues[which] : defaultSize;
                    sp.edit().putString("sub_size", val).apply();
                    applySubtitleStyle();
                    dialog.dismiss();
                    Toast.makeText(this, "Ukuran subtitle disimpan", Toast.LENGTH_SHORT).show();
                })
                .setNegativeButton("Batal", null)
                .show();
    }

    @Override
    protected void onUserLeaveHint() {
        super.onUserLeaveHint();
        if (isPipSupported() && player != null && player.isPlaying()) {
            enterPipMode();
        }
    }

    @Override
    public void onPictureInPictureModeChanged(boolean isInPictureInPictureMode, Configuration newConfig) {
        super.onPictureInPictureModeChanged(isInPictureInPictureMode, newConfig);
        if (isInPictureInPictureMode) {
            if (playerView != null) {
                playerView.hideController();
                playerView.setUseController(false);
            }
            if (layoutTopBar != null) layoutTopBar.setVisibility(View.GONE);
            if (layoutPortraitBottom != null) layoutPortraitBottom.setVisibility(View.GONE);
            if (btnScreenLock != null) btnScreenLock.setVisibility(View.GONE);
            if (btnScreenUnlock != null) btnScreenUnlock.setVisibility(View.GONE);
            if (btnSkipOpEd != null) btnSkipOpEd.setVisibility(View.GONE);
            if (hudOsd != null) hudOsd.setVisibility(View.GONE);
            if (hudHoldSpeed != null) hudHoldSpeed.setVisibility(View.GONE);

            if (tvSubtitles != null) {
                tvSubtitles.setTextSize(TypedValue.COMPLEX_UNIT_SP, 10f);
                ViewGroup.MarginLayoutParams lp = (ViewGroup.MarginLayoutParams) tvSubtitles.getLayoutParams();
                if (lp != null) {
                    lp.bottomMargin = (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 4, getResources().getDisplayMetrics());
                    tvSubtitles.setLayoutParams(lp);
                }
                int padX = (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 6, getResources().getDisplayMetrics());
                int padY = (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 2, getResources().getDisplayMetrics());
                tvSubtitles.setPadding(padX, padY, padX, padY);
            }
        } else {
            if (playerView != null) {
                playerView.setUseController(true);
            }
            applySubtitleStyle();

            int orientation = getResources().getConfiguration().orientation;
            if (orientation == Configuration.ORIENTATION_PORTRAIT) {
                if (layoutPortraitBottom != null) {
                    layoutPortraitBottom.setVisibility(View.VISIBLE);
                }
            }
            applySystemUiVisibility();
            updatePipParams();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N && isInPictureInPictureMode()) {
            return;
        }
        if (isHoldingSpeed) stopHoldingSpeed();
        if (isHoldingRewind) stopHoldingRewind();
        isVideoPlaying = false;
        recordWatchProgress(true);
        if (player != null) player.pause();
        if (hapticGenerator instanceof HapticGenerator && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            HapticGeneratorHelper.setEnabled((HapticGenerator) hapticGenerator, false);
        }
        handler.removeCallbacks(subtitleSyncRunnable);
        handler.removeCallbacks(preResolveRunnable);
    }

    @Override
    protected void onStop() {
        super.onStop();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N && isInPictureInPictureMode()) {
            return;
        }
        if (player != null) {
            player.pause();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N && isInPictureInPictureMode()) {
            return;
        }
        applySystemUiVisibility();
        SharedPreferences sp = getSharedPreferences("tatap_player_prefs", MODE_PRIVATE);
        isGeneralHapticEnabled = !TvFocusHelper.isTv(this) && sp.getBoolean("pref_general_haptic", sp.getBoolean("pref_haptic", true));
        isHapticEnabled = isGeneralHapticEnabled;
        isSceneHapticEnabled = !TvFocusHelper.isTv(this) && sp.getBoolean("pref_scene_haptic", false);
        updateHapticGeneratorState();
        if (player != null && player.isPlaying()) {
            handler.removeCallbacks(subtitleSyncRunnable);
            handler.post(subtitleSyncRunnable);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        isVideoPlaying = false;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && backInvokedCallback != null) {
            try {
                getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(backInvokedCallback);
            } catch (Throwable ignored) {}
            backInvokedCallback = null;
        }
        if (pipReceiver != null) {
            try {
                unregisterReceiver(pipReceiver);
            } catch (Throwable ignored) {}
            pipReceiver = null;
        }
        recordWatchProgress(true);
        handler.removeCallbacks(subtitleSyncRunnable);
        handler.removeCallbacks(preResolveRunnable);
        handler.removeCallbacks(hideTopBarRunnable);
        handler.removeCallbacks(hideUnlockButtonRunnable);
        releaseHapticGenerator();
        if (player != null) {
            player.release();
            player = null;
        }
    }

    public boolean isPipSupported() {
        return !TvFocusHelper.isTv(this)
                && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                && getPackageManager().hasSystemFeature(PackageManager.FEATURE_PICTURE_IN_PICTURE);
    }

    public void enterPipMode() {
        if (!isPipSupported() || player == null) return;

        if (playerView != null) {
            playerView.hideController();
        }
        if (layoutTopBar != null) layoutTopBar.setVisibility(View.GONE);
        if (layoutPortraitBottom != null) layoutPortraitBottom.setVisibility(View.GONE);
        if (btnScreenLock != null) btnScreenLock.setVisibility(View.GONE);
        if (btnScreenUnlock != null) btnScreenUnlock.setVisibility(View.GONE);
        if (btnSkipOpEd != null) btnSkipOpEd.setVisibility(View.GONE);
        if (hudOsd != null) hudOsd.setVisibility(View.GONE);
        if (hudHoldSpeed != null) hudHoldSpeed.setVisibility(View.GONE);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try {
                PictureInPictureParams params = buildPipParams();
                if (params != null) {
                    enterPictureInPictureMode(params);
                }
            } catch (Throwable t) {
                Toast.makeText(this, "Gagal masuk mode PiP: " + t.getMessage(), Toast.LENGTH_SHORT).show();
            }
        }
    }

    private PictureInPictureParams buildPipParams() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return null;

        PictureInPictureParams.Builder builder = new PictureInPictureParams.Builder();

        // 1. Native Video Aspect Ratio
        Rational rational = new Rational(16, 9);
        if (player != null && player.getVideoSize() != null && player.getVideoSize().width > 0 && player.getVideoSize().height > 0) {
            int w = player.getVideoSize().width;
            int h = player.getVideoSize().height;
            float ratio = (float) w / (float) h;
            if (ratio >= 0.418410f && ratio <= 2.39f) {
                rational = new Rational(w, h);
            }
        }
        builder.setAspectRatio(rational);

        // 2. Source Rect Hint
        if (playerView != null) {
            Rect sourceRect = new Rect();
            playerView.getGlobalVisibleRect(sourceRect);
            if (!sourceRect.isEmpty()) {
                builder.setSourceRectHint(sourceRect);
            }
        }

        // 3. Android 12+ (API 31) Auto-Enter and Seamless Resize
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            builder.setAutoEnterEnabled(player != null && player.isPlaying());
            builder.setSeamlessResizeEnabled(true);
        }

        // 4. Remote Actions
        ArrayList<RemoteAction> actions = new ArrayList<>();

        // Action 1: Mundur 10 detik
        Intent rewindIntent = new Intent(ACTION_PIP_CONTROL).putExtra(EXTRA_PIP_ACTION, PIP_ACTION_REWIND);
        rewindIntent.setPackage(getPackageName());
        PendingIntent rewindPendingIntent = PendingIntent.getBroadcast(this, PIP_ACTION_REWIND, rewindIntent, PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0));
        Icon rewindIcon = Icon.createWithResource(this, R.drawable.ic_replay_10);
        actions.add(new RemoteAction(rewindIcon, "Mundur 10d", "Mundur 10 detik", rewindPendingIntent));

        // Action 2: Play / Pause
        boolean isPlaying = (player != null && player.isPlaying());
        Intent playPauseIntent = new Intent(ACTION_PIP_CONTROL).putExtra(EXTRA_PIP_ACTION, PIP_ACTION_PLAY_PAUSE);
        playPauseIntent.setPackage(getPackageName());
        PendingIntent playPausePendingIntent = PendingIntent.getBroadcast(this, PIP_ACTION_PLAY_PAUSE, playPauseIntent, PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0));
        Icon playPauseIcon = Icon.createWithResource(this, isPlaying ? R.drawable.ic_pause : R.drawable.ic_play);
        actions.add(new RemoteAction(playPauseIcon, isPlaying ? "Jeda" : "Putar", isPlaying ? "Jeda video" : "Putar video", playPausePendingIntent));

        // Action 3: Maju 10 detik
        Intent forwardIntent = new Intent(ACTION_PIP_CONTROL).putExtra(EXTRA_PIP_ACTION, PIP_ACTION_FORWARD);
        forwardIntent.setPackage(getPackageName());
        PendingIntent forwardPendingIntent = PendingIntent.getBroadcast(this, PIP_ACTION_FORWARD, forwardIntent, PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0));
        Icon forwardIcon = Icon.createWithResource(this, R.drawable.ic_forward_10);
        actions.add(new RemoteAction(forwardIcon, "Maju 10d", "Maju 10 detik", forwardPendingIntent));

        builder.setActions(actions);

        return builder.build();
    }

    private void updatePipParams() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && isPipSupported()) {
            try {
                PictureInPictureParams params = buildPipParams();
                if (params != null) {
                    setPictureInPictureParams(params);
                }
            } catch (Throwable ignored) {}
        }
    }

    private void registerPipReceiver() {
        if (pipReceiver == null && isPipSupported()) {
            pipReceiver = new BroadcastReceiver() {
                @Override
                public void onReceive(Context context, Intent intent) {
                    if (intent == null || !ACTION_PIP_CONTROL.equals(intent.getAction())) return;
                    int action = intent.getIntExtra(EXTRA_PIP_ACTION, 0);
                    if (player == null) return;
                    switch (action) {
                        case PIP_ACTION_REWIND:
                            long newRewindPos = Math.max(0, player.getCurrentPosition() - 10000);
                            player.seekTo(newRewindPos);
                            break;
                        case PIP_ACTION_PLAY_PAUSE:
                            if (player.isPlaying()) {
                                player.pause();
                            } else {
                                player.play();
                            }
                            updatePipParams();
                            break;
                        case PIP_ACTION_FORWARD:
                            long duration = player.getDuration();
                            long newForwardPos = (duration > 0) ? Math.min(duration, player.getCurrentPosition() + 10000) : player.getCurrentPosition() + 10000;
                            player.seekTo(newForwardPos);
                            break;
                    }
                }
            };
            IntentFilter filter = new IntentFilter(ACTION_PIP_CONTROL);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                registerReceiver(pipReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
            } else {
                registerReceiver(pipReceiver, filter);
            }
        }
    }

    private void recordWatchProgress(boolean force) {
        if (player == null || slug == null || slug.isEmpty()) return;
        long now = System.currentTimeMillis();
        if (!force && (now - lastProgressSaveMs < 5000)) return;
        lastProgressSaveMs = now;

        long pos = player.getCurrentPosition();
        long dur = player.getDuration();
        if (pos <= 0 && !force) return;

        final int progSec = (int) (pos / 1000);
        final int durSec = dur > 0 ? (int) (dur / 1000) : 0;
        final String curSlug = slug;
        final int curEp = ep;

        try {
            SharedPreferences sp = getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
            sp.edit()
                    .putLong("prog_" + curSlug + "_" + curEp, pos)
                    .putLong("dur_" + curSlug + "_" + curEp, dur)
                    .apply();
        } catch (Throwable ignored) {}

        new Thread(() -> {
            try {
                JSONObject b = new JSONObject();
                b.put("slug", curSlug);
                b.put("episode", curEp);
                b.put("progress", progSec);
                b.put("duration", durSec);

                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/progress").openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                conn.setConnectTimeout(2000);
                conn.setReadTimeout(2000);
                java.io.OutputStream os = conn.getOutputStream();
                os.write(b.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
                os.close();
                conn.getResponseCode();
                conn.disconnect();
            } catch (Exception ignored) {}
        }).start();
    }

    private void checkAndPromptResume() {
        if (hasPromptedResume || slug == null || slug.isEmpty()) return;
        hasPromptedResume = true;

        long localSavedMs = 0;
        long localDurMs = 0;
        try {
            SharedPreferences sp = getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
            localSavedMs = sp.getLong("prog_" + slug + "_" + ep, 0);
            localDurMs = sp.getLong("dur_" + slug + "_" + ep, 0);
        } catch (Throwable ignored) {}

        if (localSavedMs >= 15_000) {
            if (localDurMs <= 30_000 || localSavedMs < (localDurMs - 30_000)) {
                showResumeDialog(localSavedMs);
                return;
            }
        }

        final String curSlug = slug;
        final int curEp = ep;
        new Thread(() -> {
            try {
                String u = "http://127.0.0.1:8767/api/progress?slug=" + URLEncoder.encode(curSlug, "UTF-8")
                        + "&ep=" + curEp;
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setConnectTimeout(2000);
                conn.setReadTimeout(2000);
                if (conn.getResponseCode() == 200) {
                    BufferedReader r = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder sb = new StringBuilder();
                    String l;
                    while ((l = r.readLine()) != null) sb.append(l);
                    r.close();
                    JSONObject res = new JSONObject(sb.toString());
                    if (res.optBoolean("success")) {
                        JSONObject d = res.optJSONObject("data");
                        if (d != null && d.optBoolean("should_resume", false)) {
                            long progMs = d.optLong("progress", 0) * 1000;
                            if (progMs >= 15_000) {
                                runOnUiThread(() -> showResumeDialog(progMs));
                            }
                        }
                    }
                }
                conn.disconnect();
            } catch (Exception ignored) {}
        }).start();
    }

    private void showResumeDialog(long savedMs) {
        if (isFinishing() || isDestroyed()) return;
        long sec = savedMs / 1000;
        String timeStr = String.format("%02d:%02d", sec / 60, sec % 60);

        AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
        builder.setTitle("Lanjutkan Menonton?");
        builder.setMessage("Anda sebelumnya menonton episode ini hingga menit " + timeStr + ".\nLanjutkan dari posisi terakhir atau mulai dari awal?");

        builder.setPositiveButton("Lanjutkan (" + timeStr + ")", (dialog, which) -> {
            pendingResumePosMs = savedMs;
            if (player != null && player.getPlaybackState() == Player.STATE_READY) {
                player.seekTo(savedMs);
                player.play();
            }
        });

        builder.setNegativeButton("Mulai dari Awal", (dialog, which) -> {
            pendingResumePosMs = 0;
            try {
                SharedPreferences sp = getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
                sp.edit().putLong("prog_" + slug + "_" + ep, 0).apply();
            } catch (Throwable ignored) {}
            new Thread(() -> {
                try {
                    String u = "http://127.0.0.1:8767/api/progress?slug=" + URLEncoder.encode(slug != null ? slug : "", "UTF-8")
                            + "&ep=" + ep;
                    HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                    conn.setRequestMethod("DELETE");
                    conn.setConnectTimeout(2000);
                    conn.getResponseCode();
                    conn.disconnect();
                } catch (Exception ignored) {}
            }).start();

            if (player != null && player.getPlaybackState() == Player.STATE_READY) {
                player.seekTo(0);
                player.play();
            }
        });

        builder.setOnCancelListener(dialog -> {
            if (pendingResumePosMs < 0) {
                pendingResumePosMs = savedMs;
                if (player != null && player.getPlaybackState() == Player.STATE_READY) {
                    player.seekTo(savedMs);
                    player.play();
                }
            }
        });

        AlertDialog dialog = builder.create();
        dialog.show();

        if (TvFocusHelper.isTv(this)) {
            Button btnPos = dialog.getButton(DialogInterface.BUTTON_POSITIVE);
            if (btnPos != null) {
                btnPos.requestFocus();
            }
        }
    }

    private void setupExoNativeControls() {
        if (playerView == null) return;
        playerView.post(() -> {
            bindExoControlButtons();
            updateExoButtonStates();
        });
    }

    private void bindExoControlButtons() {
        if (playerView == null) return;

        androidx.media3.ui.TimeBar timeBar = playerView.findViewById(androidx.media3.ui.R.id.exo_progress);
        if (timeBar != null && !isTimeBarListenerAttached) {
            isTimeBarListenerAttached = true;
            timeBar.addListener(new androidx.media3.ui.TimeBar.OnScrubListener() {
                private long lastScrubStep = -1;

                @Override
                public void onScrubStart(androidx.media3.ui.TimeBar timeBar, long position) {
                    lastScrubStep = position / 5000;
                    HapticHelper.performClick(playerView);
                }

                @Override
                public void onScrubMove(androidx.media3.ui.TimeBar timeBar, long position) {
                    long step = position / 5000;
                    if (step != lastScrubStep) {
                        lastScrubStep = step;
                        HapticHelper.performTick(playerView);
                    }
                }

                @Override
                public void onScrubStop(androidx.media3.ui.TimeBar timeBar, long position, boolean canceled) {
                    lastScrubStep = -1;
                    HapticHelper.performClick(playerView);
                }
            });
        }

        if (btnExoNext == null) {
            btnExoNext = playerView.findViewById(androidx.media3.ui.R.id.exo_next);
            if (btnExoNext != null) {
                btnExoNext.setOnClickListener(v -> {
                    HapticHelper.performClick(v);
                    playNextEpisode();
                });
                TvFocusHelper.attachFocusScale(btnExoNext, 1.15f, 6f);
            }
        }
        if (btnExoPrev == null) {
            btnExoPrev = playerView.findViewById(androidx.media3.ui.R.id.exo_prev);
            if (btnExoPrev != null) {
                btnExoPrev.setOnClickListener(v -> {
                    HapticHelper.performClick(v);
                    playPrevEpisode();
                });
                TvFocusHelper.attachFocusScale(btnExoPrev, 1.15f, 6f);
            }
        }
        if (btnExoSub == null) {
            btnExoSub = playerView.findViewById(androidx.media3.ui.R.id.exo_subtitle);
            if (btnExoSub != null) {
                btnExoSub.setVisibility(View.VISIBLE);
                btnExoSub.setOnClickListener(v -> {
                    HapticHelper.performClick(v);
                    showSubtitleSelectorDialog();
                });
                TvFocusHelper.attachFocusScale(btnExoSub, 1.15f, 6f);
            }
        }
        if (btnExoSettings == null) {
            btnExoSettings = playerView.findViewById(androidx.media3.ui.R.id.exo_settings);
            if (btnExoSettings != null) {
                btnExoSettings.setVisibility(View.VISIBLE);
                btnExoSettings.setOnClickListener(v -> {
                    HapticHelper.performClick(v);
                    showPlayerUnifiedSettingsDialog();
                });
                TvFocusHelper.attachFocusScale(btnExoSettings, 1.15f, 6f);
            }
        }
        if (btnExoFullscreen == null) {
            btnExoFullscreen = playerView.findViewById(androidx.media3.ui.R.id.exo_fullscreen);
            if (btnExoFullscreen != null) {
                btnExoFullscreen.setVisibility(View.VISIBLE);
                btnExoFullscreen.setOnClickListener(v -> {
                    HapticHelper.performClick(v);
                    if (TvFocusHelper.isTv(this)) {
                        cycleAspectRatio();
                    } else {
                        int orient = getResources().getConfiguration().orientation;
                        if (orient == Configuration.ORIENTATION_LANDSCAPE) {
                            exitLandscapeFullscreen();
                        } else {
                            setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
                        }
                    }
                });
                TvFocusHelper.attachFocusScale(btnExoFullscreen, 1.15f, 6f);
            }
        }
    }

    private void updateExoButtonStates() {
        runOnUiThread(() -> {
            bindExoControlButtons();
            boolean hasNext = hasNextEpisode();
            boolean hasPrev = hasPrevEpisode();
            boolean isTv = TvFocusHelper.isTv(this);
            boolean isPaused = (player != null && !player.isPlaying());

            boolean enableNext = hasNext && (!isTv || isPaused);
            boolean enablePrev = hasPrev && (!isTv || isPaused);

            if (btnExoNext != null) {
                btnExoNext.setEnabled(enableNext);
                btnExoNext.setFocusable(enableNext);
                btnExoNext.setAlpha(enableNext ? 1.0f : 0.25f);
            }
            if (btnExoPrev != null) {
                btnExoPrev.setEnabled(enablePrev);
                btnExoPrev.setFocusable(enablePrev);
                btnExoPrev.setAlpha(enablePrev ? 1.0f : 0.25f);
            }
            if (btnExoSub != null) {
                btnExoSub.setAlpha(subEnabled ? 1.0f : 0.45f);
            }
            if (btnSubSelector != null) {
                btnSubSelector.setAlpha(subEnabled ? 1.0f : 0.6f);
            }
        });
    }

    private void showPlayerUnifiedSettingsDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
        builder.setTitle("Pengaturan Pemutar");

        SharedPreferences sp = getSharedPreferences("tatap_player_prefs", MODE_PRIVATE);
        boolean autoSkip = sp.getBoolean("auto_skip_op_ed", false);
        String spdLabel = formatSpeedLabel(currentPlaybackSpeed);
        String qLabel = activeQuality != null && !activeQuality.isEmpty() ? activeQuality.toUpperCase() : "AUTO";
        String subLabel = !subEnabled ? "Mati" : (activeSubLang.toUpperCase() + " [" + activeEngine + "]");
        String autoSkipLabel = autoSkip ? "Aktif" : "Mati";

        List<String> menuList = new ArrayList<>();
        List<Runnable> actionList = new ArrayList<>();

        if (TvFocusHelper.isTv(this)) {
            if (hasNextEpisode()) {
                menuList.add("Putar Episode Berikutnya (Ep " + getNextEpisodeNumber() + ")");
                actionList.add(this::playNextEpisode);
            }
            if (hasPrevEpisode()) {
                menuList.add("Putar Episode Sebelumnya (Ep " + getPrevEpisodeNumber() + ")");
                actionList.add(this::playPrevEpisode);
            }
        }

        menuList.add("Kecepatan Putar Video (" + spdLabel + ")");
        actionList.add(this::showSpeedSelectorDialog);

        menuList.add("Pilihan Subtitle & Terjemahan (" + subLabel + ")");
        actionList.add(this::showSubtitleSelectorDialog);

        menuList.add("Pilihan Kualitas Video (" + qLabel + ")");
        actionList.add(this::showQualitySelectorDialog);

        menuList.add("Pengaturan Tampilan & Gaya Subtitle");
        actionList.add(this::showSubtitleStyleDialog);

        menuList.add("Skala Layar / Rasio Aspek (" + getAspectLabel() + ")");
        actionList.add(this::cycleAspectRatio);

        menuList.add("Otomatis Lewati Opening & Ending (" + autoSkipLabel + ")");
        actionList.add(() -> {
            boolean newAutoSkip = !autoSkip;
            sp.edit().putBoolean("auto_skip_op_ed", newAutoSkip).apply();
            autoSkipOpEd = newAutoSkip;
            Toast.makeText(this, "Otomatis Lewati OP/ED: " + (newAutoSkip ? "Aktif" : "Mati"), Toast.LENGTH_SHORT).show();
        });

        String[] menuArray = menuList.toArray(new String[0]);
        builder.setItems(menuArray, (dialog, which) -> {
            if (which >= 0 && which < actionList.size()) {
                actionList.get(which).run();
            }
        });

        builder.setNegativeButton("Tutup", (dialog, which) -> dialog.dismiss());
        builder.setOnDismissListener(dialog -> {
            if (playerView != null) {
                playerView.showController();
                if (btnExoSettings != null && btnExoSettings.getVisibility() == View.VISIBLE) {
                    btnExoSettings.requestFocus();
                } else if (btnSpeed != null && btnSpeed.getVisibility() == View.VISIBLE) {
                    btnSpeed.requestFocus();
                } else if (btnQuality != null && btnQuality.getVisibility() == View.VISIBLE) {
                    btnQuality.requestFocus();
                }
            }
        });
        builder.show();
    }

    private String getAspectLabel() {
        if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_ZOOM) {
            return "Zoom";
        } else if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_FILL) {
            return "Fill";
        } else {
            return "Fit";
        }
    }

    private void ensureEpisodeListLoaded() {
        if ((!episodeList.isEmpty() && episodeList.size() > 1) || isEpisodeListLoading || slug == null || slug.isEmpty()) return;
        isEpisodeListLoading = true;
        new Thread(() -> {
            try {
                String u = "http://127.0.0.1:8767/api/anime/" + URLEncoder.encode(slug, "UTF-8") + "/episodes";
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setConnectTimeout(8000);
                conn.setReadTimeout(12000);
                int code = conn.getResponseCode();
                InputStream is = (code >= 200 && code < 400) ? conn.getInputStream() : conn.getErrorStream();
                if (is != null) {
                    BufferedReader reader = new BufferedReader(new InputStreamReader(is));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) sb.append(line);
                    reader.close();
                    JSONObject res = new JSONObject(sb.toString());
                    if (res.optBoolean("success")) {
                        JSONArray epsArr = res.getJSONObject("data").getJSONArray("episodes");
                        List<Integer> list = new ArrayList<>();
                        for (int i = 0; i < epsArr.length(); i++) {
                            list.add(epsArr.getJSONObject(i).getInt("ep"));
                        }
                        java.util.Collections.sort(list);
                        runOnUiThread(() -> {
                            if (!list.isEmpty()) {
                                episodeList.clear();
                                episodeList.addAll(list);
                                updateExoButtonStates();
                                preResolveNeighbors();
                                updatePortraitEpisodeDisplay();
                            }
                        });
                    }
                }
                conn.disconnect();
            } catch (Exception ignored) {}
            isEpisodeListLoading = false;
        }).start();
    }

    private boolean hasNextEpisode() {
        if (episodeList != null && !episodeList.isEmpty()) {
            int idx = episodeList.indexOf(ep);
            if (idx >= 0) {
                return idx < episodeList.size() - 1;
            }
            for (int e : episodeList) {
                if (e > ep) return true;
            }
            return false;
        }
        return true;
    }

    private boolean hasPrevEpisode() {
        if (episodeList != null && !episodeList.isEmpty()) {
            int idx = episodeList.indexOf(ep);
            if (idx >= 0) {
                return idx > 0;
            }
            for (int e : episodeList) {
                if (e < ep) return true;
            }
            return ep > 1;
        }
        return ep > 1;
    }

    private int getNextEpisodeNumber() {
        if (episodeList != null && !episodeList.isEmpty()) {
            int idx = episodeList.indexOf(ep);
            if (idx >= 0 && idx < episodeList.size() - 1) {
                return episodeList.get(idx + 1);
            }
            for (int e : episodeList) {
                if (e > ep) return e;
            }
        }
        return ep + 1;
    }

    private int getPrevEpisodeNumber() {
        if (episodeList != null && !episodeList.isEmpty()) {
            int idx = episodeList.indexOf(ep);
            if (idx > 0) {
                return episodeList.get(idx - 1);
            }
            int prev = -1;
            for (int e : episodeList) {
                if (e < ep) {
                    if (prev == -1 || e > prev) prev = e;
                }
            }
            if (prev != -1) return prev;
        }
        return Math.max(1, ep - 1);
    }

    private void playNextEpisode() {
        int nextEp = getNextEpisodeNumber();
        switchEpisode(nextEp);
    }

    private void playPrevEpisode() {
        int prevEp = getPrevEpisodeNumber();
        switchEpisode(prevEp);
    }

    private void switchEpisode(int targetEp) {
        if (ep == targetEp) return;
        performHapticClick();
        recordWatchProgress(true);
        ep = targetEp;
        hasPromptedResume = false;
        pendingResumePosMs = -1;
        checkAndPromptResume();

        currentResolveLoadId++;
        final int thisResolveId = currentResolveLoadId;

        currentSubLoadId++;
        currentCues = new ArrayList<>();
        if (tvSubtitles != null) {
            tvSubtitles.setText("");
            tvSubtitles.setVisibility(View.GONE);
        }
        rawStreamUrl = "";
        activeSubUrl = "";
        masterStreamUrl = "";
        subtitleTracks.clear();
        hasFallbackAttempted = false;
        hasAutoRetriedStream = false;
        consecutiveRecoveryAttempts = 0;
        introStartMs = 0;
        introEndMs = 0;
        outroStartMs = 0;
        outroEndMs = 0;
        hasAutoSkippedIntro = false;
        hasAutoSkippedOutro = false;
        currentSkipTargetMs = 0;
        if (btnSkipOpEd != null) {
            btnSkipOpEd.setVisibility(View.GONE);
        }

        if (player != null) {
            player.stop();
            player.clearMediaItems();
        }

        if (title != null && !title.isEmpty()) {
            tvPlayerTitle.setText(title + " - Ep " + ep);
        } else {
            tvPlayerTitle.setText("Episode " + ep);
        }

        try {
            SharedPreferences histSp = getSharedPreferences("tatap_history", Context.MODE_PRIVATE);
            histSp.edit()
                    .putInt("last_ep_" + slug, ep)
                    .putBoolean("watched_" + slug + "_" + ep, true)
                    .apply();
        } catch (Throwable ignored) {}

        updatePortraitEpisodeDisplay();
        updateExoButtonStates();

        if (layoutBuffering != null) {
            layoutBuffering.setVisibility(View.VISIBLE);
            if (tvBufferingText != null) {
                tvBufferingText.setText("MEMUAT EPISODE " + ep + "...");
                tvBufferingText.setVisibility(View.VISIBLE);
            }
        }

        // Rekam episode baru ke riwayat
        new Thread(() -> {
            try {
                JSONObject b = new JSONObject();
                b.put("slug", slug != null ? slug : "");
                b.put("title", title != null ? title : "");
                b.put("episode", ep);
                b.put("mode", "sub");
                b.put("progress", 0);

                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/history").openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                conn.setConnectTimeout(3000);
                java.io.OutputStream os = conn.getOutputStream();
                os.write(b.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
                os.close();
                conn.getResponseCode();
                conn.disconnect();
            } catch (Exception ignored) {}
        }).start();

        resolveAndPlayStream(thisResolveId);
    }

    /**
     * Pre-resolve URL episode sebelum (N-1) dan sesudah (N+1) secara background.
     * ZERO VIDEO PRE-BUFFERING:
     * Hanya meminta metadata JSON stream/subtitle ke server backend lokal (yang akan
     * di-scrape & disimpan ke SQLite episode_cache). Tidak mengunduh segmen video .ts
     * atau buffer video ExoPlayer untuk menjaga konsumsi RAM dan kuota tetap minimal.
     */
    private final Runnable preResolveRunnable = this::executePreResolveNeighbors;

    private void preResolveNeighbors() {
        if (TvFocusHelper.isTv(this)) {
            // Pada TV, tunda preResolve 20 detik setelah pemutaran stabil agar tidak berebut CPU/RAM hardware decoder
            handler.removeCallbacks(preResolveRunnable);
            handler.postDelayed(preResolveRunnable, 20_000);
            return;
        }
        executePreResolveNeighbors();
    }

    private void executePreResolveNeighbors() {
        final String currentSlug = (slug != null) ? slug : "";
        final String currentQ = (activeQuality != null && !activeQuality.isEmpty()) ? activeQuality : "best";

        if (currentSlug.isEmpty()) return;

        List<Integer> targets = new ArrayList<>();
        if (hasNextEpisode()) {
            targets.add(getNextEpisodeNumber());
        }
        if (hasPrevEpisode()) {
            targets.add(getPrevEpisodeNumber());
        }

        if (targets.isEmpty()) return;

        new Thread(() -> {
            for (int targetEp : targets) {
                try {
                    String u = "http://127.0.0.1:8767/api/stream/resolve?slug="
                            + URLEncoder.encode(currentSlug, "UTF-8")
                            + "&ep=" + targetEp
                            + "&mode=sub&q=" + URLEncoder.encode(currentQ, "UTF-8");
                    HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                    conn.setConnectTimeout(15000);
                    conn.setReadTimeout(20000);
                    int respCode = conn.getResponseCode();
                    if (respCode == 200) {
                        BufferedReader r = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                        while (r.readLine() != null) {}
                        r.close();
                    }
                    conn.disconnect();
                } catch (Exception ignored) {}
            }
        }).start();
    }

    private void updatePortraitEpisodeDisplay() {
        if (TvFocusHelper.isTv(this) || layoutPortraitBottom == null) return;

        if (title != null && !title.isEmpty()) {
            if (tvPortraitAnimeTitle != null) tvPortraitAnimeTitle.setText(title);
        }
        if (tvPortraitCurrentEp != null) {
            tvPortraitCurrentEp.setText("Memutar Episode " + ep);
        }

        if (episodeList == null || episodeList.isEmpty()) {
            if (tvPortraitEpCount != null) tvPortraitEpCount.setText("Daftar Episode");
            return;
        }

        if (tvPortraitEpCount != null) {
            tvPortraitEpCount.setText("Daftar Episode (" + episodeList.size() + ")");
        }

        // Build ranges if size > 30
        if (episodeList.size() > 30) {
            portraitRanges.clear();
            int minEp = episodeList.get(0);
            int maxEp = episodeList.get(episodeList.size() - 1);
            int rangeSize = 30;
            PortraitEpisodeRange foundActiveRange = null;
            for (int s = minEp; s <= maxEp; s += rangeSize) {
                int e = Math.min(s + rangeSize - 1, maxEp);
                PortraitEpisodeRange r = new PortraitEpisodeRange(s, e);
                portraitRanges.add(r);
                if (ep >= s && ep <= e) {
                    foundActiveRange = r;
                }
            }
            if (activePortraitRange == null || foundActiveRange != null) {
                activePortraitRange = foundActiveRange != null ? foundActiveRange : portraitRanges.get(0);
            }
            if (rvPortraitRanges != null) {
                rvPortraitRanges.setVisibility(View.VISIBLE);
                if (portraitRangeAdapter != null) {
                    portraitRangeAdapter.setRanges(portraitRanges, activePortraitRange);
                }
            }
        } else {
            activePortraitRange = null;
            if (rvPortraitRanges != null) {
                rvPortraitRanges.setVisibility(View.GONE);
            }
        }

        // Filter list based on range
        List<Integer> filtered = new ArrayList<>();
        for (int e : episodeList) {
            if (activePortraitRange == null || (e >= activePortraitRange.start && e <= activePortraitRange.end)) {
                filtered.add(e);
            }
        }

        if (!isPortraitAscending) {
            java.util.Collections.reverse(filtered);
        }

        if (portraitEpisodeAdapter != null) {
            portraitEpisodeAdapter.setEpisodes(filtered);
            int targetPos = filtered.indexOf(ep);
            if (targetPos >= 0 && rvPortraitEpisodes != null) {
                rvPortraitEpisodes.scrollToPosition(targetPos);
            }
        }
    }

    private class PortraitEpisodeAdapter extends RecyclerView.Adapter<PortraitEpisodeAdapter.EpViewHolder> {
        private final List<Integer> items = new ArrayList<>();
        private final java.util.Set<Integer> watchedSet = new java.util.HashSet<>();

        public void setEpisodes(List<Integer> list) {
            items.clear();
            watchedSet.clear();
            if (list != null) {
                items.addAll(list);
                try {
                    SharedPreferences hist = getSharedPreferences("tatap_history", Context.MODE_PRIVATE);
                    for (int itemEp : list) {
                        if (hist.getBoolean("watched_" + slug + "_" + itemEp, false)) {
                            watchedSet.add(itemEp);
                        }
                    }
                } catch (Throwable ignored) {}
            }
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public EpViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View v = getLayoutInflater().inflate(R.layout.item_episode, parent, false);
            return new EpViewHolder(v);
        }

        @Override
        public void onBindViewHolder(@NonNull EpViewHolder holder, int position) {
            int itemEp = items.get(position);
            holder.tvTitle.setText(String.valueOf(itemEp));

            if (itemEp == ep) {
                // Active playing episode: Apple Blue highlight
                holder.card.setCardBackgroundColor(0xFF1E2B45);
                holder.card.setStrokeColor(0xFF0A84FF);
                holder.card.setStrokeWidth(dpToPx(1));
                holder.tvTitle.setTextColor(0xFF0A84FF);
                holder.tvBadge.setVisibility(View.VISIBLE);
                holder.tvBadge.setText("MEMUTAR");
                holder.tvBadge.setTextColor(0xFF0A84FF);
            } else if (watchedSet.contains(itemEp)) {
                // Watched episode
                holder.card.setCardBackgroundColor(0xFF0E1017);
                holder.card.setStrokeColor(0xFF1C202C);
                holder.card.setStrokeWidth(dpToPx(1));
                holder.tvTitle.setTextColor(0xFF64748B);
                holder.tvBadge.setVisibility(View.VISIBLE);
                holder.tvBadge.setText("DITONTON");
                holder.tvBadge.setTextColor(0xFF10B981);
            } else {
                // Unwatched episode
                holder.card.setCardBackgroundColor(0xFF11141C);
                holder.card.setStrokeColor(0xFF1C202C);
                holder.card.setStrokeWidth(dpToPx(1));
                holder.tvTitle.setTextColor(0xFFF1F5F9);
                holder.tvBadge.setVisibility(View.GONE);
            }

            holder.itemView.setOnClickListener(v -> {
                if (itemEp != ep) {
                    HapticHelper.performClick(v);
                    switchEpisode(itemEp);
                }
            });
        }

        @Override
        public int getItemCount() {
            return items.size();
        }

        class EpViewHolder extends RecyclerView.ViewHolder {
            com.google.android.material.card.MaterialCardView card;
            TextView tvTitle;
            TextView tvBadge;

            public EpViewHolder(@NonNull View itemView) {
                super(itemView);
                card = itemView.findViewById(R.id.card_episode);
                tvTitle = itemView.findViewById(R.id.tv_ep_title);
                tvBadge = itemView.findViewById(R.id.tv_ep_status_badge);
            }
        }
    }

    private class PortraitRangeAdapter extends RecyclerView.Adapter<PortraitRangeAdapter.RangeViewHolder> {
        private final List<PortraitEpisodeRange> ranges = new ArrayList<>();
        private PortraitEpisodeRange selectedRange;

        public void setRanges(List<PortraitEpisodeRange> list, PortraitEpisodeRange selected) {
            ranges.clear();
            if (list != null) ranges.addAll(list);
            this.selectedRange = selected;
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public RangeViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View v = getLayoutInflater().inflate(R.layout.item_range_chip, parent, false);
            return new RangeViewHolder(v);
        }

        @Override
        public void onBindViewHolder(@NonNull RangeViewHolder holder, int position) {
            PortraitEpisodeRange r = ranges.get(position);
            holder.tvLabel.setText(r.label);
            boolean isSel = (selectedRange != null && selectedRange.label.equals(r.label));
            if (isSel) {
                holder.card.setCardBackgroundColor(0xFF1E293B);
                holder.card.setStrokeColor(0xFF38BDF8);
                holder.tvLabel.setTextColor(0xFF38BDF8);
            } else {
                holder.card.setCardBackgroundColor(0xFF161B26);
                holder.card.setStrokeColor(0xFF2A3347);
                holder.tvLabel.setTextColor(0xFF94A3B8);
            }
            holder.itemView.setOnClickListener(v -> {
                HapticHelper.performTick(v);
                selectedRange = r;
                activePortraitRange = r;
                notifyDataSetChanged();
                updatePortraitEpisodeDisplay();
            });
        }

        @Override
        public int getItemCount() {
            return ranges.size();
        }

        class RangeViewHolder extends RecyclerView.ViewHolder {
            com.google.android.material.card.MaterialCardView card;
            TextView tvLabel;

            public RangeViewHolder(@NonNull View itemView) {
                super(itemView);
                card = itemView.findViewById(R.id.card_range_chip);
                tvLabel = itemView.findViewById(R.id.tv_range_label);
            }
        }
    }

    @Override
    public void onTrimMemory(int level) {
        super.onTrimMemory(level);
        if (level >= TRIM_MEMORY_RUNNING_LOW) {
            ImageLoader.trimMemory();
            if (TvFocusHelper.isTv(this)) {
                new Thread(() -> {
                    try {
                        Class<?> pyClass = Class.forName("com.chaquo.python.Python");
                        if ((Boolean) pyClass.getMethod("isStarted").invoke(null)) {
                            Object pyInstance = pyClass.getMethod("getInstance").invoke(null);
                            Object launcherMod = pyClass.getMethod("getModule", String.class).invoke(pyInstance, "server_launcher");
                            launcherMod.getClass().getMethod("callAttr", String.class, Object[].class).invoke(launcherMod, "trim_memory", new Object[]{});
                        }
                    } catch (Throwable ignored) {}
                }).start();
            }
        }
    }
}
