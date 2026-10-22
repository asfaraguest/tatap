package id.tatap.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.Editable;
import android.text.TextWatcher;
import android.transition.AutoTransition;
import android.transition.TransitionManager;
import android.util.Log;
import android.animation.ValueAnimator;
import android.view.animation.DecelerateInterpolator;
import android.view.ViewParent;
import android.view.FocusFinder;
import android.view.HapticFeedbackConstants;
import android.content.SharedPreferences;
import android.view.KeyEvent;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.inputmethod.EditorInfo;
import android.graphics.PorterDuff;
import android.graphics.drawable.Drawable;
import android.text.Spannable;
import android.text.SpannableString;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import androidx.core.graphics.drawable.DrawableCompat;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends Activity {
    private static final String TAG = "TatapMain";

    private EditText etSearch;
    private TextView btnClearSearch;
    private ProgressBar pbLoading;
    private View layoutLoadingState;
    private TextView tvLoadingLabel;
    private TextView tvSectionTitle, tvItemCount, tvPageIndicator;
    private ImageView btnStatusPower;
    private RecyclerView rvGrid;
    private AnimeAdapter adapter;
    private SwipeRefreshLayout swipeRefreshLayout;

    // Header & Unified Fluid Search Bar
    private ViewGroup layoutHeaderRoot;
    private View layoutSearchBox;
    private TextView btnToggleMenu;

    // Android TV Docked Sidebar (Autohide / Collapsed Rail 64dp <-> Expanded 210dp)
    private View layoutTvSidebar;
    private View layoutTvBrand;
    private TextView tvAppLogo;
    private TextView tvBadgeTv;
    private LinearLayout layoutTvBottomControls;
    private boolean isTvSidebarExpanded = true;
    private ValueAnimator tvSidebarAnimator;

    // In-memory tab cache untuk peralihan instan (<1ms) & race condition tokenization
    private static class TabCacheEntry {
        final List<JSONObject> items;
        final int count;
        final int totalPages;
        final boolean hasNextPage;
        final boolean hasPagingInfo;
        final long timestamp;

        TabCacheEntry(List<JSONObject> items, int count, int totalPages, boolean hasNextPage, boolean hasPagingInfo) {
            this.items = items;
            this.count = count;
            this.totalPages = totalPages;
            this.hasNextPage = hasNextPage;
            this.hasPagingInfo = hasPagingInfo;
            this.timestamp = System.currentTimeMillis();
        }

        boolean isExpired() {
            return (System.currentTimeMillis() - timestamp) > 180000L; // TTL 3 menit
        }
    }

    private final java.util.Map<String, TabCacheEntry> tabDataCache = new java.util.concurrent.ConcurrentHashMap<>();
    private final java.util.concurrent.atomic.AtomicInteger currentFetchToken = new java.util.concurrent.atomic.AtomicInteger(0);

    // Header Quick Actions (Retained for backward safety)
    private TextView btnHeaderAi, btnHeaderGenre, btnHeaderHelp, btnHeaderHistory;

    // Scrollable Category Pills & Pagination
    private View layoutTabsSegmented;
    private LinearLayout layoutTabsContainer;
    private TextView btnTabMusim, btnTabAiring, btnTabJadwal, btnTabRiwayat, btnTabFavorit, btnTabKatalog, btnTabGenre;
    private View layoutScheduleDays;
    private TextView btnDaySenin, btnDaySelasa, btnDayRabu, btnDayKamis, btnDayJumat, btnDaySabtu, btnDayMinggu;
    private String currentScheduleDay = "today"; // "monday".."sunday" | "today" | "yesterday" | "tomorrow"
    private String currentScheduleActualDay = ""; // actual weekday key dari backend (misal "thursday")
    private TextView btnPrevPage, btnNextPage;
    private View layoutPagination;

    // Empty / Error State Layout
    private View layoutEmptyState;
    private TextView tvEmptyTitle, tvEmptyDesc, btnEmptyRetry;

    // Command Banner & Active Filter Bar Widgets
    private View layoutCommandBanner;
    private TextView tvCommandOutput;
    private Button btnCloseCommandBanner;
    private View layoutActiveFilter;
    private TextView tvActiveFilterLabel;
    private Button btnClearFilter;
    private TextView btnClearHistoryAll;
    private TextView btnFilterCatalog;

    private final Handler bannerHandler = new Handler(Looper.getMainLooper());
    private final Runnable hideBannerRunnable = () -> hideCommandBanner(true);

    // State navigasi tampilan & paging
    private String currentView = "musim"; // "musim" | "airing" | "katalog" | "cari" | "genre" | "season_filter" | "riwayat"
    private String currentSearchQuery = "";
    private String currentGenre = "";
    private String currentSeasonName = "";
    private int currentSeasonYear = 0;
    private int currentPage = 1;
    private int totalPages = 1;
    private boolean hasNextPage = false;
    private boolean hasPagingInfo = false;

    // State Cross Filter Katalog (Urutan + Tahun + Musim + Bulan + Tipe + Status)
    private String filterCatalogSort = "popularity";
    private String filterCatalogYear = "";
    private String filterCatalogSeason = "";
    private String filterCatalogMonth = "";
    private String filterCatalogType = "";
    private String filterCatalogStatus = "";
    private long lastBackPressTime = 0L;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        layoutHeaderRoot = findViewById(R.id.layout_header_root);
        layoutSearchBox = findViewById(R.id.layout_search_box);
        btnToggleMenu = findViewById(R.id.btn_toggle_menu);

        layoutTvSidebar = findViewById(R.id.layout_tv_sidebar);
        layoutTvBrand = findViewById(R.id.layout_tv_brand);
        tvAppLogo = findViewById(R.id.tv_app_logo);
        tvBadgeTv = findViewById(R.id.tv_badge_tv);
        layoutTvBottomControls = findViewById(R.id.layout_tv_bottom_controls);

        etSearch = findViewById(R.id.et_search);
        btnClearSearch = findViewById(R.id.btn_clear_search);
        pbLoading = findViewById(R.id.pb_central_loading);
        layoutLoadingState = findViewById(R.id.layout_loading_state);
        tvSectionTitle = findViewById(R.id.tv_section_title);
        tvItemCount = findViewById(R.id.tv_item_count);
        btnStatusPower = findViewById(R.id.btn_status_power);
        tvLoadingLabel = findViewById(R.id.tv_loading_label);
        tvPageIndicator = findViewById(R.id.tv_page_indicator);
        rvGrid = findViewById(R.id.rv_anime_grid);
        swipeRefreshLayout = findViewById(R.id.swipe_refresh_layout);

        updateBackendStatusUI(0);
        showLoadingState("Memulai backend Tatap...");

        layoutTabsSegmented = findViewById(R.id.layout_tabs_segmented);
        layoutTabsContainer = findViewById(R.id.layout_tabs_container);
        btnTabMusim = findViewById(R.id.btn_tab_musim);
        btnTabAiring = findViewById(R.id.btn_tab_airing);
        btnTabJadwal = findViewById(R.id.btn_tab_jadwal);
        btnTabRiwayat = findViewById(R.id.btn_tab_riwayat);
        btnTabFavorit = findViewById(R.id.btn_tab_favorit);
        btnTabKatalog = findViewById(R.id.btn_tab_katalog);
        btnTabGenre = findViewById(R.id.btn_tab_genre);
        layoutScheduleDays = findViewById(R.id.layout_schedule_days);
        btnDaySenin = findViewById(R.id.btn_day_senin);
        btnDaySelasa = findViewById(R.id.btn_day_selasa);
        btnDayRabu = findViewById(R.id.btn_day_rabu);
        btnDayKamis = findViewById(R.id.btn_day_kamis);
        btnDayJumat = findViewById(R.id.btn_day_jumat);
        btnDaySabtu = findViewById(R.id.btn_day_sabtu);
        btnDayMinggu = findViewById(R.id.btn_day_minggu);

        // Tab Jadwal & Riwayat aktif untuk APK Mobile dan Android TV
        if (btnTabJadwal != null) {
            btnTabJadwal.setVisibility(View.VISIBLE);
            if (TvFocusHelper.isTv(this)) {
                TvFocusHelper.attachFocusScale(btnTabJadwal, 1.05f, 4f);
            }
        }
        if (btnTabRiwayat != null) {
            btnTabRiwayat.setVisibility(View.VISIBLE);
            if (TvFocusHelper.isTv(this)) {
                TvFocusHelper.attachFocusScale(btnTabRiwayat, 1.05f, 4f);
            }
        }
        if (TvFocusHelper.isTv(this)) {
            TextView[] scheduleChips = {btnDaySenin, btnDaySelasa, btnDayRabu, btnDayKamis, btnDayJumat, btnDaySabtu, btnDayMinggu};
            for (int i = 0; i < scheduleChips.length; i++) {
                TextView chip = scheduleChips[i];
                if (chip != null) {
                    TvFocusHelper.attachFocusScale(chip, 1.06f, 4f);
                    chip.setNextFocusUpId(R.id.btn_tab_jadwal);
                    chip.setNextFocusDownId(R.id.rv_anime_grid);
                    if (i > 0 && scheduleChips[i - 1] != null) {
                        chip.setNextFocusLeftId(scheduleChips[i - 1].getId());
                    } else {
                        chip.setNextFocusLeftId(R.id.btn_tab_jadwal);
                    }
                    if (i < scheduleChips.length - 1 && scheduleChips[i + 1] != null) chip.setNextFocusRightId(scheduleChips[i + 1].getId());
                }
            }
        }

        btnPrevPage = findViewById(R.id.btn_prev_page);
        btnNextPage = findViewById(R.id.btn_next_page);
        layoutPagination = findViewById(R.id.layout_pagination);

        layoutEmptyState = findViewById(R.id.layout_empty_state);
        tvEmptyTitle = findViewById(R.id.tv_empty_title);
        tvEmptyDesc = findViewById(R.id.tv_empty_desc);
        btnEmptyRetry = findViewById(R.id.btn_empty_retry);

        // Command HUD & Filter Bar
        layoutCommandBanner = findViewById(R.id.layout_command_banner);
        tvCommandOutput = findViewById(R.id.tv_command_output);
        btnCloseCommandBanner = findViewById(R.id.btn_close_command_banner);
        layoutActiveFilter = findViewById(R.id.layout_active_filter);
        tvActiveFilterLabel = findViewById(R.id.tv_active_filter_label);
        btnClearFilter = findViewById(R.id.btn_clear_filter);
        btnClearHistoryAll = findViewById(R.id.btn_clear_history_all);
        btnFilterCatalog = findViewById(R.id.btn_filter_catalog);
        if (btnFilterCatalog != null) {
            btnFilterCatalog.setOnClickListener(v -> showCatalogFilterDialog());
            TvFocusHelper.attachFocusScale(btnFilterCatalog, 1.08f, 4f);
        }
        if (tvActiveFilterLabel != null) {
            tvActiveFilterLabel.setOnClickListener(v -> {
                if ("katalog".equals(currentView)) {
                    showCatalogFilterDialog();
                } else if ("genre".equals(currentView)) {
                    showGenreSelectorDialog();
                }
            });
        }

        int spanCount = getResources().getInteger(R.integer.anime_grid_columns);
        GridLayoutManager glm = new GridLayoutManager(this, spanCount);
        adapter = new AnimeAdapter(this);
        glm.setSpanSizeLookup(new GridLayoutManager.SpanSizeLookup() {
            @Override
            public int getSpanSize(int position) {
                return (adapter != null && adapter.isHeader(position)) ? glm.getSpanCount() : 1;
            }
        });
        rvGrid.setLayoutManager(glm);
        rvGrid.setAdapter(adapter);
        // Performance tuning: bedakan antara Android TV (ramah low-RAM STB & 60 FPS) dan Mobile
        rvGrid.setHasFixedSize(true);
        if (TvFocusHelper.isTv(this)) {
            // Pada TV: hilangkan layout animation agar tidak membebani GPU TV Stick
            rvGrid.setLayoutAnimation(null);
            // Sediakan cache 10 view (cukup untuk 1 baris atas & bawah) tanpa boros RAM (< 1.5MB)
            rvGrid.setItemViewCacheSize(10);
            RecyclerView.RecycledViewPool pool = new RecyclerView.RecycledViewPool();
            pool.setMaxRecycledViews(0, 12);
            rvGrid.setRecycledViewPool(pool);
        } else {
            rvGrid.setItemViewCacheSize(20);
            rvGrid.setDrawingCacheEnabled(true);
            rvGrid.setDrawingCacheQuality(View.DRAWING_CACHE_QUALITY_LOW);
        }

        setupTabsAndListeners();

        if (TvFocusHelper.isTv(this)) {
            applyTvTopBarCompression();
            setupTvSidebarFocusListener();
            btnTabMusim.post(() -> btnTabMusim.requestFocus());
        }

        // 1. Jalankan backend Python lokal
        startEmbeddedBackend();

        // 2. Tunggu backend siap lalu muat konten pertama
        waitForServerAndLoadCatalog(0);

        handleIncomingIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIncomingIntent(intent);
    }

    private void handleIncomingIntent(Intent intent) {
        if (intent != null && intent.hasExtra("genre")) {
            String targetGenre = intent.getStringExtra("genre");
            if (targetGenre != null && !targetGenre.trim().isEmpty()) {
                setGenreFilter(targetGenre.trim());
            }
        }
    }

    private void setupTvSidebarFocusListener() {
        if (layoutTvSidebar == null || !TvFocusHelper.isTv(this)) return;
        layoutTvSidebar.getViewTreeObserver().addOnGlobalFocusChangeListener((oldFocus, newFocus) -> {
            if (newFocus == null || !TvFocusHelper.isTv(this)) return;
            boolean insideSidebar = isViewDescendantOf(newFocus, layoutTvSidebar);
            if (insideSidebar && !isTvSidebarExpanded) {
                setTvSidebarExpanded(true, true);
            } else if (!insideSidebar && isTvSidebarExpanded) {
                setTvSidebarExpanded(false, true);
            }
        });
    }

    private boolean isViewDescendantOf(View child, View parent) {
        if (child == null || parent == null) return false;
        if (child == parent) return true;
        ViewParent p = child.getParent();
        while (p != null) {
            if (p == parent) return true;
            p = p.getParent();
        }
        return false;
    }

    private void setTvSidebarExpanded(boolean expand, boolean animate) {
        if (layoutTvSidebar == null || !TvFocusHelper.isTv(this)) return;
        isTvSidebarExpanded = expand;

        int targetWidth = expand ? dpToPx(210) : dpToPx(64);
        int targetPaddingStart = expand ? dpToPx(16) : dpToPx(8);
        int targetPaddingEnd = expand ? dpToPx(12) : dpToPx(8);

        if (tvSidebarAnimator != null && tvSidebarAnimator.isRunning()) {
            tvSidebarAnimator.cancel();
        }

        if (animate) {
            int startWidth = layoutTvSidebar.getWidth();
            if (startWidth <= 0) startWidth = expand ? dpToPx(64) : dpToPx(210);
            tvSidebarAnimator = ValueAnimator.ofInt(startWidth, targetWidth);
            tvSidebarAnimator.setDuration(200);
            tvSidebarAnimator.setInterpolator(new DecelerateInterpolator());
            tvSidebarAnimator.addUpdateListener(anim -> {
                int val = (Integer) anim.getAnimatedValue();
                ViewGroup.LayoutParams lp = layoutTvSidebar.getLayoutParams();
                if (lp != null) {
                    lp.width = val;
                    layoutTvSidebar.setLayoutParams(lp);
                }
            });
            tvSidebarAnimator.start();
        } else {
            ViewGroup.LayoutParams lp = layoutTvSidebar.getLayoutParams();
            if (lp != null) {
                lp.width = targetWidth;
                layoutTvSidebar.setLayoutParams(lp);
            }
        }

        layoutTvSidebar.setPadding(targetPaddingStart, dpToPx(20), targetPaddingEnd, dpToPx(16));

        // 1. App Brand Logo
        if (layoutTvBrand != null && tvAppLogo != null) {
            if (expand) {
                tvAppLogo.setText("TATAP");
                if (tvBadgeTv != null) tvBadgeTv.setVisibility(View.VISIBLE);
                if (layoutTvBrand instanceof LinearLayout) {
                    ((LinearLayout) layoutTvBrand).setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
                }
                layoutTvBrand.setPadding(dpToPx(6), 0, dpToPx(6), 0);
            } else {
                tvAppLogo.setText("T");
                if (tvBadgeTv != null) tvBadgeTv.setVisibility(View.GONE);
                if (layoutTvBrand instanceof LinearLayout) {
                    ((LinearLayout) layoutTvBrand).setGravity(Gravity.CENTER);
                }
                layoutTvBrand.setPadding(0, 0, 0, 0);
            }
        }

        // 2. Quick Search Box
        if (layoutSearchBox != null && etSearch != null) {
            if (expand) {
                etSearch.setHint("Cari anime...");
                layoutSearchBox.setPadding(dpToPx(10), 0, dpToPx(10), 0);
                etSearch.setPadding(0, 0, 0, 0);
                if (btnClearSearch != null) {
                    btnClearSearch.setVisibility(etSearch.getText().length() > 0 ? View.VISIBLE : View.GONE);
                }
            } else {
                etSearch.setHint("");
                layoutSearchBox.setPadding(0, 0, 0, 0);
                etSearch.setPadding(dpToPx(12), 0, 0, 0);
                if (btnClearSearch != null) {
                    btnClearSearch.setVisibility(View.GONE);
                }
            }
        }

        // 3. Navigation Tabs
        TextView[] tvTabs = new TextView[]{btnTabMusim, btnTabAiring, btnTabJadwal, btnTabRiwayat, btnTabFavorit, btnTabKatalog, btnTabGenre};
        for (TextView tab : tvTabs) {
            if (tab == null) continue;
            if (expand) {
                tab.setText(getTabTitleString(tab));
                tab.setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
                tab.setPadding(dpToPx(10), 0, dpToPx(10), 0);
            } else {
                tab.setText("");
                tab.setGravity(Gravity.CENTER);
                tab.setPadding(0, 0, 0, 0);
            }
        }

        // 4. Bottom Controls (Server Status & Menu)
        if (layoutTvBottomControls != null && btnStatusPower != null && btnToggleMenu != null) {
            if (expand) {
                layoutTvBottomControls.setOrientation(LinearLayout.HORIZONTAL);
                layoutTvBottomControls.setGravity(Gravity.CENTER_VERTICAL);

                LinearLayout.LayoutParams lpPower = new LinearLayout.LayoutParams(dpToPx(36), dpToPx(36));
                btnStatusPower.setLayoutParams(lpPower);

                LinearLayout.LayoutParams lpMenu = new LinearLayout.LayoutParams(0, dpToPx(36), 1.0f);
                lpMenu.setMarginStart(dpToPx(8));
                btnToggleMenu.setLayoutParams(lpMenu);
                btnToggleMenu.setText("Menu");
                btnToggleMenu.setGravity(Gravity.CENTER);
                btnToggleMenu.setPadding(0, 0, 0, 0);

                btnStatusPower.setNextFocusRightId(R.id.btn_toggle_menu);
                btnStatusPower.setNextFocusDownId(R.id.btn_status_power);
                btnToggleMenu.setNextFocusLeftId(R.id.btn_status_power);
                btnToggleMenu.setNextFocusUpId(R.id.btn_tab_genre);
                btnToggleMenu.setNextFocusRightId(R.id.rv_anime_grid);
                btnToggleMenu.setNextFocusDownId(R.id.btn_toggle_menu);
            } else {
                layoutTvBottomControls.setOrientation(LinearLayout.VERTICAL);
                layoutTvBottomControls.setGravity(Gravity.CENTER_HORIZONTAL);

                LinearLayout.LayoutParams lpPower = new LinearLayout.LayoutParams(dpToPx(36), dpToPx(36));
                lpPower.gravity = Gravity.CENTER_HORIZONTAL;
                btnStatusPower.setLayoutParams(lpPower);

                LinearLayout.LayoutParams lpMenu = new LinearLayout.LayoutParams(dpToPx(36), dpToPx(36));
                lpMenu.gravity = Gravity.CENTER_HORIZONTAL;
                lpMenu.topMargin = dpToPx(6);
                btnToggleMenu.setLayoutParams(lpMenu);
                btnToggleMenu.setText("");
                btnToggleMenu.setGravity(Gravity.CENTER);
                btnToggleMenu.setPadding(0, 0, 0, 0);

                btnStatusPower.setNextFocusDownId(R.id.btn_toggle_menu);
                btnStatusPower.setNextFocusRightId(R.id.rv_anime_grid);
                btnToggleMenu.setNextFocusUpId(R.id.btn_status_power);
                btnToggleMenu.setNextFocusLeftId(R.id.btn_toggle_menu);
                btnToggleMenu.setNextFocusRightId(R.id.rv_anime_grid);
                btnToggleMenu.setNextFocusDownId(R.id.btn_toggle_menu);
            }
        }
    }

    private void applyTvTopBarCompression() {
        if (!TvFocusHelper.isTv(this)) return;

        boolean isVerticalSidebar = (layoutTabsContainer != null && layoutTabsContainer.getOrientation() == LinearLayout.VERTICAL);
        if (isVerticalSidebar) {
            // Android TV Left Sidebar (Apple Flat 10-Foot UI):
            TextView[] tvTabs = new TextView[]{btnTabMusim, btnTabAiring, btnTabJadwal, btnTabRiwayat, btnTabFavorit, btnTabKatalog, btnTabGenre};
            for (int i = 0; i < tvTabs.length; i++) {
                TextView tab = tvTabs[i];
                if (tab != null) {
                    LinearLayout.LayoutParams tlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dpToPx(38));
                    tlp.setMargins(0, dpToPx(2), 0, dpToPx(2));
                    tab.setLayoutParams(tlp);
                    tab.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f);
                    tab.setNextFocusRightId(R.id.rv_anime_grid);
                    tab.setNextFocusLeftId(tab.getId());
                    tab.setNextFocusUpId(i == 0 ? R.id.layout_search_box : tvTabs[i - 1].getId());
                    tab.setNextFocusDownId(i == tvTabs.length - 1 ? R.id.btn_status_power : tvTabs[i + 1].getId());
                }
            }

            if (layoutSearchBox != null) {
                layoutSearchBox.setNextFocusUpId(R.id.layout_search_box);
                layoutSearchBox.setNextFocusDownId(R.id.btn_tab_musim);
                layoutSearchBox.setNextFocusRightId(R.id.rv_anime_grid);
                layoutSearchBox.setNextFocusLeftId(R.id.layout_search_box);
            }
            if (btnStatusPower != null) {
                btnStatusPower.setNextFocusUpId(R.id.btn_tab_genre);
                btnStatusPower.setNextFocusRightId(isTvSidebarExpanded ? R.id.btn_toggle_menu : R.id.rv_anime_grid);
                btnStatusPower.setNextFocusLeftId(R.id.btn_status_power);
                btnStatusPower.setNextFocusDownId(isTvSidebarExpanded ? R.id.btn_status_power : R.id.btn_toggle_menu);
            }
            if (btnToggleMenu != null) {
                btnToggleMenu.setNextFocusUpId(isTvSidebarExpanded ? R.id.btn_tab_genre : R.id.btn_status_power);
                btnToggleMenu.setNextFocusLeftId(isTvSidebarExpanded ? R.id.btn_status_power : R.id.btn_toggle_menu);
                btnToggleMenu.setNextFocusRightId(R.id.rv_anime_grid);
                btnToggleMenu.setNextFocusDownId(R.id.btn_toggle_menu);
            }
            setTvSidebarExpanded(isTvSidebarExpanded, false);
            updateTabButtons();
            return;
        }

        if (layoutHeaderRoot != null) {
            ViewGroup.LayoutParams lp = layoutHeaderRoot.getLayoutParams();
            if (lp != null) {
                lp.height = dpToPx(44);
                layoutHeaderRoot.setLayoutParams(lp);
            }
        }
        if (layoutSearchBox != null) {
            ViewGroup.LayoutParams lp = layoutSearchBox.getLayoutParams();
            if (lp != null) {
                lp.height = dpToPx(34);
                layoutSearchBox.setLayoutParams(lp);
            }
        }
        if (btnToggleMenu != null) {
            ViewGroup.LayoutParams lp = btnToggleMenu.getLayoutParams();
            if (lp != null) {
                lp.height = dpToPx(34);
                btnToggleMenu.setLayoutParams(lp);
            }
        }
        if (layoutTabsSegmented != null) {
            ViewGroup.MarginLayoutParams mlp = (ViewGroup.MarginLayoutParams) layoutTabsSegmented.getLayoutParams();
            if (mlp != null) {
                mlp.topMargin = dpToPx(2);
                mlp.bottomMargin = dpToPx(4);
                layoutTabsSegmented.setLayoutParams(mlp);
            }
            layoutTabsSegmented.setPadding(0, 0, 0, 0);
        }

        if (layoutTabsContainer != null) {
            ViewGroup.LayoutParams clp = layoutTabsContainer.getLayoutParams();
            if (clp != null) {
                clp.width = ViewGroup.LayoutParams.MATCH_PARENT;
                clp.height = dpToPx(42);
                layoutTabsContainer.setLayoutParams(clp);
            }
        }
        // Pada Android TV horizontal layout (fallback), seluruh 7 tab
        // dibagikan rata (weight=1.0f) membentang penuh 100% menyesuaikan lebar layar TV (10-Foot UI)
        TextView[] tvTabs = new TextView[]{btnTabMusim, btnTabAiring, btnTabJadwal, btnTabRiwayat, btnTabFavorit, btnTabKatalog, btnTabGenre};
        for (int i = 0; i < tvTabs.length; i++) {
            TextView tab = tvTabs[i];
            if (tab != null) {
                LinearLayout.LayoutParams tlp = new LinearLayout.LayoutParams(0, dpToPx(38), 1.0f);
                tlp.setMarginEnd(i < tvTabs.length - 1 ? dpToPx(6) : 0);
                tab.setLayoutParams(tlp);
                tab.setGravity(Gravity.CENTER);
                tab.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f);
                tab.setPadding(dpToPx(6), 0, dpToPx(6), 0);
                // Kosongkan compound drawable XML agar tidak terpisah ke tepi kiri,
                // di TV digantikan oleh CenteredImageSpan inline di updateTvTabSpannable()
                tab.setCompoundDrawablesWithIntrinsicBounds(null, null, null, null);
            }
        }

        // Hubungkan D-Pad spasial horizontal header TV:
        if (layoutSearchBox != null) {
            layoutSearchBox.setNextFocusRightId(R.id.btn_status_power);
            layoutSearchBox.setNextFocusDownId(R.id.btn_tab_musim);
        }
        if (btnStatusPower != null) {
            btnStatusPower.setNextFocusLeftId(R.id.layout_search_box);
            btnStatusPower.setNextFocusRightId(R.id.btn_toggle_menu);
            btnStatusPower.setNextFocusDownId(R.id.btn_tab_riwayat);
        }
        if (btnToggleMenu != null) {
            btnToggleMenu.setNextFocusLeftId(R.id.btn_status_power);
            btnToggleMenu.setNextFocusDownId(R.id.btn_tab_genre);
        }

        // Hubungkan panah ATAS dari tab ke elemen header yang tepat:
        if (btnTabMusim != null) btnTabMusim.setNextFocusUpId(R.id.layout_search_box);
        if (btnTabAiring != null) btnTabAiring.setNextFocusUpId(R.id.layout_search_box);
        if (btnTabJadwal != null) btnTabJadwal.setNextFocusUpId(R.id.layout_search_box);
        if (btnTabRiwayat != null) btnTabRiwayat.setNextFocusUpId(R.id.btn_status_power);
        if (btnTabFavorit != null) btnTabFavorit.setNextFocusUpId(R.id.btn_status_power);
        if (btnTabKatalog != null) btnTabKatalog.setNextFocusUpId(R.id.btn_toggle_menu);
        if (btnTabGenre != null) btnTabGenre.setNextFocusUpId(R.id.btn_toggle_menu);

        // Sambungkan rantai D-Pad horizontal penuh 7 tab tanpa ada yang ter-skip:
        if (btnTabMusim != null) {
            btnTabMusim.setNextFocusLeftId(R.id.btn_tab_musim);
            btnTabMusim.setNextFocusRightId(R.id.btn_tab_airing);
        }
        if (btnTabAiring != null) {
            btnTabAiring.setNextFocusLeftId(R.id.btn_tab_musim);
            btnTabAiring.setNextFocusRightId(R.id.btn_tab_jadwal);
        }
        if (btnTabJadwal != null) {
            btnTabJadwal.setNextFocusLeftId(R.id.btn_tab_airing);
            btnTabJadwal.setNextFocusRightId(R.id.btn_tab_riwayat);
        }
        if (btnTabRiwayat != null) {
            btnTabRiwayat.setNextFocusLeftId(R.id.btn_tab_jadwal);
            btnTabRiwayat.setNextFocusRightId(R.id.btn_tab_favorit);
        }
        if (btnTabFavorit != null) {
            btnTabFavorit.setNextFocusLeftId(R.id.btn_tab_riwayat);
            btnTabFavorit.setNextFocusRightId(R.id.btn_tab_katalog);
        }
        if (btnTabKatalog != null) {
            btnTabKatalog.setNextFocusLeftId(R.id.btn_tab_favorit);
            btnTabKatalog.setNextFocusRightId(R.id.btn_tab_genre);
        }
        if (btnTabGenre != null) {
            btnTabGenre.setNextFocusLeftId(R.id.btn_tab_katalog);
            btnTabGenre.setNextFocusRightId(R.id.btn_tab_genre);
        }

        updateTabButtons();
    }

    private void setupDialogWindowBounds(Dialog dialog) {
        if (dialog == null || dialog.getWindow() == null) return;
        dialog.getWindow().setBackgroundDrawable(new ColorDrawable(Color.TRANSPARENT));
        int width = TvFocusHelper.isTv(this)
                ? Math.min(dpToPx(700), (int) (getResources().getDisplayMetrics().widthPixels * 0.80f))
                : ViewGroup.LayoutParams.MATCH_PARENT;
        dialog.getWindow().setLayout(width, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private int dpToPx(int dp) {
        return (int) (dp * getResources().getDisplayMetrics().density + 0.5f);
    }

    /**
     * Mengupdate warna dan background indikator icon server backend.
     * @param state 1 = Online (Hijau), 0 = Checking / Booting (Kuning), 2 = Offline / Error (Merah)
     */
    private void updateBackendStatusUI(int state) {
        if (btnStatusPower == null) return;
        if (state == 1) { // Online
            btnStatusPower.setColorFilter(0xFF10B981, PorterDuff.Mode.SRC_IN);
            btnStatusPower.setBackgroundResource(R.drawable.bg_status_pill);
        } else if (state == 0) { // Checking / Booting
            btnStatusPower.setColorFilter(0xFFF59E0B, PorterDuff.Mode.SRC_IN);
            btnStatusPower.setBackgroundResource(R.drawable.bg_status_pill_warn);
        } else { // Offline / Error
            btnStatusPower.setColorFilter(0xFFEF4444, PorterDuff.Mode.SRC_IN);
            btnStatusPower.setBackgroundResource(R.drawable.bg_status_pill_err);
        }
    }

    private void showLoadingState(String message) {
        if (layoutLoadingState != null) {
            if (tvLoadingLabel != null && message != null) {
                tvLoadingLabel.setText(message);
            }
            layoutLoadingState.setVisibility(View.VISIBLE);
        }
        if (rvGrid != null) {
            rvGrid.setAlpha(0.25f);
        }
        if (layoutEmptyState != null) {
            layoutEmptyState.setVisibility(View.GONE);
        }
    }

    private void setupTabsAndListeners() {
        if (btnToggleMenu != null) {
            btnToggleMenu.setOnClickListener(v -> showCommandHelpDialog());
        }

        etSearch.setOnEditorActionListener((v, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_SEARCH ||
                    (event != null && event.getKeyCode() == KeyEvent.KEYCODE_ENTER && event.getAction() == KeyEvent.ACTION_DOWN)) {
                hideKeyboard();
                etSearch.clearFocus();
                String raw = etSearch.getText().toString().trim();
                if (!raw.isEmpty()) {
                    if (raw.startsWith(":") || raw.startsWith("/")) {
                        executeCommand(raw.substring(1).trim());
                    } else {
                        currentView = "cari";
                        currentSearchQuery = raw;
                        currentPage = 1;
                        totalPages = 1;
                        hasNextPage = false;
                        hasPagingInfo = false;
                        updateTabButtons();
                        updateActiveFilterBar();
                        showCommandOutput("> tatap$ cari \"" + raw + "\"", false);
                        fetchData();
                    }
                }
                return true;
            }
            return false;
        });

        if (TvFocusHelper.isTv(this)) {
            if (layoutSearchBox != null) {
                layoutSearchBox.setFocusable(true);
                TvFocusHelper.attachFocusScale(layoutSearchBox, 1.04f, 4f);
            }
            if (etSearch != null) {
                etSearch.setFocusable(false);
                etSearch.setFocusableInTouchMode(false);
            }
        }

        if (layoutSearchBox != null) {
            layoutSearchBox.setOnClickListener(v -> activateSearchInput());
            layoutSearchBox.setOnKeyListener((v, keyCode, event) -> {
                if (event.getAction() == KeyEvent.ACTION_DOWN) {
                    if (keyCode == KeyEvent.KEYCODE_DPAD_CENTER || keyCode == KeyEvent.KEYCODE_ENTER) {
                        activateSearchInput();
                        return true;
                    }
                }
                return false;
            });
        }

        if (etSearch != null) {
            etSearch.setOnClickListener(v -> activateSearchInput());
            etSearch.setOnKeyListener((v, keyCode, event) -> {
                if (event.getAction() == KeyEvent.ACTION_DOWN) {
                    if (keyCode == KeyEvent.KEYCODE_BACK) {
                        hideKeyboard();
                        etSearch.clearFocus();
                        if (TvFocusHelper.isTv(this)) {
                            etSearch.setFocusable(false);
                            etSearch.setFocusableInTouchMode(false);
                            if (layoutSearchBox != null) layoutSearchBox.requestFocus();
                        }
                        return true;
                    } else if (keyCode == KeyEvent.KEYCODE_DPAD_DOWN) {
                        hideKeyboard();
                        etSearch.clearFocus();
                        if (TvFocusHelper.isTv(this)) {
                            etSearch.setFocusable(false);
                            etSearch.setFocusableInTouchMode(false);
                            if (layoutTabsSegmented != null) {
                                layoutTabsSegmented.requestFocus();
                            } else if (rvGrid != null) {
                                rvGrid.requestFocus();
                            }
                        }
                        return true;
                    }
                }
                return false;
            });
        }

        btnTabMusim.setOnClickListener(v -> {
            HapticHelper.performClick(v);
            resetFiltersToTab("musim");
        });

        btnTabAiring.setOnClickListener(v -> {
            HapticHelper.performClick(v);
            resetFiltersToTab("airing");
        });

        if (btnTabJadwal != null) {
            btnTabJadwal.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                resetFiltersToTab("jadwal");
            });
        }

        if (btnTabRiwayat != null) {
            btnTabRiwayat.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                resetFiltersToTab("riwayat");
            });
        }

        if (btnTabFavorit != null) {
            btnTabFavorit.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                resetFiltersToTab("favorit");
            });
        }

        btnTabKatalog.setOnClickListener(v -> {
            HapticHelper.performClick(v);
            if ("katalog".equals(currentView)) {
                showCatalogFilterDialog();
            } else {
                resetFiltersToTab("katalog");
            }
        });

        if (btnTabGenre != null) {
            btnTabGenre.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                showGenreSelectorDialog();
            });
        }

        if (btnDaySenin != null) btnDaySenin.setOnClickListener(v -> { HapticHelper.performTick(v); switchScheduleDay("monday"); });
        if (btnDaySelasa != null) btnDaySelasa.setOnClickListener(v -> { HapticHelper.performTick(v); switchScheduleDay("tuesday"); });
        if (btnDayRabu != null) btnDayRabu.setOnClickListener(v -> { HapticHelper.performTick(v); switchScheduleDay("wednesday"); });
        if (btnDayKamis != null) btnDayKamis.setOnClickListener(v -> { HapticHelper.performTick(v); switchScheduleDay("thursday"); });
        if (btnDayJumat != null) btnDayJumat.setOnClickListener(v -> { HapticHelper.performTick(v); switchScheduleDay("friday"); });
        if (btnDaySabtu != null) btnDaySabtu.setOnClickListener(v -> { HapticHelper.performTick(v); switchScheduleDay("saturday"); });
        if (btnDayMinggu != null) btnDayMinggu.setOnClickListener(v -> { HapticHelper.performTick(v); switchScheduleDay("sunday"); });

        btnPrevPage.setOnClickListener(v -> {
            if (currentPage > 1) {
                HapticHelper.performClick(v);
                currentPage--;
                showLoadingState("Memuat halaman " + currentPage + "...");
                fetchData();
            }
        });

        btnNextPage.setOnClickListener(v -> {
            HapticHelper.performClick(v);
            currentPage++;
            showLoadingState("Memuat halaman " + currentPage + "...");
            fetchData();
        });

        if (layoutCommandBanner != null) {
            layoutCommandBanner.setOnClickListener(v -> hideCommandBanner(true));
        }

        if (btnCloseCommandBanner != null) {
            btnCloseCommandBanner.setOnClickListener(v -> hideCommandBanner(true));
        }

        if (btnClearFilter != null) {
            btnClearFilter.setOnClickListener(v -> {
                if ("katalog".equals(currentView)) {
                    resetCatalogFilterState();
                    updateActiveFilterBar();
                    fetchData();
                } else {
                    resetFiltersToTab("musim");
                }
            });
        }

        if (btnHeaderAi != null) {
            btnHeaderAi.setOnClickListener(v -> {
                showAiSettingsDialog();
            });
        }

        if (btnHeaderGenre != null) {
            btnHeaderGenre.setOnClickListener(v -> {
                showGenreSelectorDialog();
            });
        }

        if (btnHeaderHelp != null) {
            btnHeaderHelp.setOnClickListener(v -> {
                showCommandHelpDialog();
            });
        }

        if (btnHeaderHistory != null) {
            btnHeaderHistory.setOnClickListener(v -> {
                resetFiltersToTab("riwayat");
            });
        }

        if (btnClearHistoryAll != null) {
            btnClearHistoryAll.setOnClickListener(v -> confirmAndClearHistory());
        }

        if (btnClearSearch != null) {
            btnClearSearch.setOnClickListener(v -> {
                HapticHelper.performTick(v);
                etSearch.setText("");
                if ("cari".equals(currentView)) {
                    resetFiltersToTab("musim");
                }
            });
        }

        etSearch.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}

            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                if (btnClearSearch != null) {
                    btnClearSearch.setVisibility(s != null && s.length() > 0 ? View.VISIBLE : View.GONE);
                }
            }

            @Override
            public void afterTextChanged(Editable s) {}
        });

        if (swipeRefreshLayout != null) {
            swipeRefreshLayout.setColorSchemeColors(0xFF00DBEB, 0xFF0E7490);
            swipeRefreshLayout.setProgressBackgroundColorSchemeColor(0xFF0E121C);
            swipeRefreshLayout.setOnRefreshListener(() -> {
                HapticHelper.performTick(swipeRefreshLayout);
                tabDataCache.clear();
                fetchData();
            });
        }

        if (btnEmptyRetry != null) {
            btnEmptyRetry.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                tabDataCache.clear();
                fetchData();
            });
        }

        if (btnStatusPower != null) {
            btnStatusPower.setOnClickListener(v -> checkBackendStatus());
        }

        // Pasang respon fokus D-Pad TV pada seluruh elemen interaktif
        TvFocusHelper.attachFocusScale(btnToggleMenu, 1.1f, 6f);
        if (btnStatusPower != null) TvFocusHelper.attachFocusScale(btnStatusPower, 1.15f, 6f);
        if (layoutSearchBox != null) TvFocusHelper.attachFocusScale(layoutSearchBox, 1.03f, 4f);
        TvFocusHelper.attachFocusScale(btnTabMusim, 1.06f, 6f);
        TvFocusHelper.attachFocusScale(btnTabAiring, 1.06f, 6f);
        if (btnTabJadwal != null) TvFocusHelper.attachFocusScale(btnTabJadwal, 1.06f, 6f);
        if (btnTabRiwayat != null) TvFocusHelper.attachFocusScale(btnTabRiwayat, 1.06f, 6f);
        if (btnTabFavorit != null) TvFocusHelper.attachFocusScale(btnTabFavorit, 1.06f, 6f);
        TvFocusHelper.attachFocusScale(btnTabKatalog, 1.06f, 6f);
        if (btnTabGenre != null) TvFocusHelper.attachFocusScale(btnTabGenre, 1.06f, 6f);
        TvFocusHelper.attachFocusScale(btnPrevPage, 1.1f, 6f);
        TvFocusHelper.attachFocusScale(btnNextPage, 1.1f, 6f);
        TvFocusHelper.attachFocusScale(btnEmptyRetry, 1.08f, 6f);
        TvFocusHelper.attachFocusScale(btnClearFilter, 1.1f, 6f);
        TvFocusHelper.attachFocusScale(btnClearHistoryAll, 1.1f, 6f);
        TvFocusHelper.attachFocusScale(btnCloseCommandBanner, 1.1f, 6f);

        TextView[] dayButtons = {btnDaySenin, btnDaySelasa, btnDayRabu, btnDayKamis, btnDayJumat, btnDaySabtu, btnDayMinggu};
        for (TextView dBtn : dayButtons) {
            if (dBtn != null) {
                TvFocusHelper.attachFocusScale(dBtn, 1.08f, 6f);
                if (TvFocusHelper.isTv(this)) {
                    dBtn.setNextFocusUpId(R.id.btn_tab_jadwal);
                    dBtn.setNextFocusDownId(R.id.rv_anime_grid);
                    if (dBtn == btnDaySenin) {
                        dBtn.setNextFocusLeftId(R.id.btn_tab_jadwal);
                    }
                }
            }
        }
    }

    private void setFoldedMenuOpen(boolean open) {
        // No-op backward safety
    }

    private void toggleFoldedMenu() {
        showCommandHelpDialog();
    }

    private TextView getActiveTabButton() {
        if ("musim".equals(currentView)) return btnTabMusim;
        if ("airing".equals(currentView)) return btnTabAiring;
        if ("jadwal".equals(currentView)) return btnTabJadwal;
        if ("katalog".equals(currentView)) return btnTabKatalog;
        if ("genre".equals(currentView)) return btnTabGenre;
        if ("riwayat".equals(currentView)) return btnTabRiwayat;
        if ("favorit".equals(currentView)) return btnTabFavorit;
        return btnTabMusim;
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            int keyCode = event.getKeyCode();
            if (keyCode == KeyEvent.KEYCODE_MENU || keyCode == KeyEvent.KEYCODE_SETTINGS) {
                showCommandHelpDialog();
                return true;
            } else if (keyCode == KeyEvent.KEYCODE_SEARCH) {
                activateSearchInput();
                return true;
            } else if (keyCode == KeyEvent.KEYCODE_DPAD_LEFT && TvFocusHelper.isTv(this)) {
                View focused = getCurrentFocus();
                if (focused != null && rvGrid != null && (focused == rvGrid || rvGrid.indexOfChild(focused) >= 0 || focused.getParent() == rvGrid)) {
                    View foundLeft = FocusFinder.getInstance().findNextFocus(rvGrid, focused, View.FOCUS_LEFT);
                    if (foundLeft == null) {
                        TextView activeTab = getActiveTabButton();
                        if (activeTab != null) {
                            activeTab.requestFocus();
                            return true;
                        }
                    }
                }
            }
        }
        return super.dispatchKeyEvent(event);
    }

    @Override
    public void onBackPressed() {
        if (etSearch != null && etSearch.hasFocus()) {
            etSearch.clearFocus();
            hideKeyboard();
            if (TvFocusHelper.isTv(this)) {
                etSearch.setFocusable(false);
                etSearch.setFocusableInTouchMode(false);
                if (layoutSearchBox != null) layoutSearchBox.requestFocus();
            }
            return;
        }
        if (!"musim".equals(currentView)) {
            resetFiltersToTab("musim");
            return;
        }
        long now = System.currentTimeMillis();
        if (now - lastBackPressTime < 2000L) {
            super.onBackPressed();
        } else {
            lastBackPressTime = now;
            Toast.makeText(this, "Tekan sekali lagi untuk keluar dari Tatap", Toast.LENGTH_SHORT).show();
        }
    }


    private void hideCommandBanner(boolean animated) {
        if (layoutCommandBanner == null || layoutCommandBanner.getVisibility() != View.VISIBLE) return;
        bannerHandler.removeCallbacks(hideBannerRunnable);
        if (animated) {
            layoutCommandBanner.animate()
                    .alpha(0f)
                    .setDuration(220)
                    .withEndAction(() -> {
                        layoutCommandBanner.setVisibility(View.GONE);
                        layoutCommandBanner.setAlpha(1.0f);
                    })
                    .start();
        } else {
            layoutCommandBanner.animate().cancel();
            layoutCommandBanner.setVisibility(View.GONE);
            layoutCommandBanner.setAlpha(1.0f);
        }
    }

    private void showCommandOutput(String message, boolean isError) {
        if (layoutCommandBanner == null || tvCommandOutput == null) return;
        layoutCommandBanner.animate().cancel();
        layoutCommandBanner.setAlpha(1.0f);
        tvCommandOutput.setText(message);
        tvCommandOutput.setTextColor(isError ? 0xFFEF4444 : 0xFF38BDF8);
        layoutCommandBanner.setVisibility(View.VISIBLE);

        bannerHandler.removeCallbacks(hideBannerRunnable);

        // Durasi baca ergonomis berdasarkan panjang teks & kategori pesan
        int len = message != null ? message.length() : 0;
        long delayMs;
        if (isError) {
            delayMs = 4500; // Error / peringatan butuh waktu baca lebih panjang
        } else if (len <= 35) {
            delayMs = 2200; // Pergantian tab / status ringkas
        } else if (len <= 65) {
            delayMs = 3200; // Notifikasi sedang
        } else {
            delayMs = 4500; // Teks panjang
        }

        bannerHandler.postDelayed(hideBannerRunnable, delayMs);
    }

    private boolean isCatalogFilterActive() {
        return !"popularity".equals(filterCatalogSort) ||
                !filterCatalogYear.isEmpty() ||
                !filterCatalogSeason.isEmpty() ||
                !filterCatalogMonth.isEmpty() ||
                !filterCatalogType.isEmpty() ||
                !filterCatalogStatus.isEmpty();
    }

    private String getCatalogFilterSummary() {
        List<String> parts = new ArrayList<>();
        if ("score".equals(filterCatalogSort)) parts.add("SKOR TERTINGGI");
        else if ("latest".equals(filterCatalogSort)) parts.add("TERBARU");
        else if ("trending".equals(filterCatalogSort)) parts.add("TRENDING");
        else if ("az".equals(filterCatalogSort)) parts.add("A-Z");
        else if ("most_favorite".equals(filterCatalogSort)) parts.add("FAVORIT");

        if (!filterCatalogYear.isEmpty()) parts.add(filterCatalogYear.toUpperCase());
        if (!filterCatalogSeason.isEmpty()) {
            if ("spring".equals(filterCatalogSeason)) parts.add("SEMI (SPRING)");
            else if ("summer".equals(filterCatalogSeason)) parts.add("PANAS (SUMMER)");
            else if ("fall".equals(filterCatalogSeason)) parts.add("GUGUR (FALL)");
            else if ("winter".equals(filterCatalogSeason)) parts.add("DINGIN (WINTER)");
            else parts.add(filterCatalogSeason.toUpperCase());
        }
        if (!filterCatalogMonth.isEmpty()) {
            String[] mNames = {"", "JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGU", "SEP", "OKT", "NOV", "DES"};
            try {
                int mi = Integer.parseInt(filterCatalogMonth);
                if (mi >= 1 && mi <= 12) parts.add(mNames[mi]);
                else parts.add("BLN " + filterCatalogMonth);
            } catch (Exception e) {
                parts.add("BLN " + filterCatalogMonth);
            }
        }
        if (!filterCatalogType.isEmpty()) parts.add(filterCatalogType.toUpperCase());
        if (!filterCatalogStatus.isEmpty()) {
            parts.add("releasing".equals(filterCatalogStatus) ? "AIRING" : "TAMAT");
        }
        if (parts.isEmpty()) return "KATALOG TERFILTER";
        StringBuilder sb = new StringBuilder("KATALOG: ");
        for (int i = 0; i < parts.size(); i++) {
            if (i > 0) sb.append(" · ");
            sb.append(parts.get(i));
        }
        return sb.toString();
    }

    private void resetCatalogFilterState() {
        filterCatalogSort = "popularity";
        filterCatalogYear = "";
        filterCatalogSeason = "";
        filterCatalogMonth = "";
        filterCatalogType = "";
        filterCatalogStatus = "";
        currentPage = 1;
    }

    private void updateActiveFilterBar() {
        if (btnFilterCatalog != null) {
            btnFilterCatalog.setVisibility("katalog".equals(currentView) ? View.VISIBLE : View.GONE);
        }
        if (layoutActiveFilter == null || tvActiveFilterLabel == null) return;

        if ("katalog".equals(currentView) && isCatalogFilterActive()) {
            layoutActiveFilter.setVisibility(View.VISIBLE);
            tvActiveFilterLabel.setText(getCatalogFilterSummary());
            if (btnClearHistoryAll != null) btnClearHistoryAll.setVisibility(View.GONE);
        } else if ("genre".equals(currentView)) {
            layoutActiveFilter.setVisibility(View.VISIBLE);
            tvActiveFilterLabel.setText("GENRE: " + currentGenre.toUpperCase().replace("-", " "));
            if (btnClearHistoryAll != null) btnClearHistoryAll.setVisibility(View.GONE);
        } else if ("season_filter".equals(currentView)) {
            layoutActiveFilter.setVisibility(View.VISIBLE);
            tvActiveFilterLabel.setText("MUSIM: " + currentSeasonName.toUpperCase() + " " + currentSeasonYear);
            if (btnClearHistoryAll != null) btnClearHistoryAll.setVisibility(View.GONE);
        } else if ("cari".equals(currentView)) {
            layoutActiveFilter.setVisibility(View.VISIBLE);
            tvActiveFilterLabel.setText("CARI: \"" + currentSearchQuery + "\"");
            if (btnClearHistoryAll != null) btnClearHistoryAll.setVisibility(View.GONE);
        } else if ("riwayat".equals(currentView)) {
            layoutActiveFilter.setVisibility(View.VISIBLE);
            tvActiveFilterLabel.setText("RIWAYAT TONTONAN");
            if (btnClearHistoryAll != null) btnClearHistoryAll.setVisibility(View.VISIBLE);
        } else if ("favorit".equals(currentView)) {
            layoutActiveFilter.setVisibility(View.VISIBLE);
            tvActiveFilterLabel.setText("ANIME FAVORIT");
            if (btnClearHistoryAll != null) btnClearHistoryAll.setVisibility(View.GONE);
        } else {
            layoutActiveFilter.setVisibility(View.GONE);
            if (btnClearHistoryAll != null) btnClearHistoryAll.setVisibility(View.GONE);
        }
    }

    private void resetFiltersToTab(String targetTab) {
        currentGenre = "";
        currentSeasonName = "";
        currentSeasonYear = 0;
        currentSearchQuery = "";
        etSearch.setText("");
        if (!"katalog".equals(targetTab)) {
            resetCatalogFilterState();
        }
        switchView(targetTab);
        updateActiveFilterBar();
        showCommandOutput("> tatap$ Tampilan diatur ke: " + targetTab.toUpperCase(), false);
    }

    private void executeCommand(String commandLine) {
        if (commandLine.isEmpty()) return;
        String[] parts = commandLine.split("\\s+");
        String cmd = parts[0].toLowerCase();
        String args = commandLine.length() > cmd.length() ? commandLine.substring(cmd.length()).trim() : "";

        switch (cmd) {
            case "help":
            case "bantuan":
            case "?":
                showCommandOutput("> tatap$ :help [Membuka Terminal Bantuan]", false);
                showCommandHelpDialog();
                break;

            case "musim":
                resetFiltersToTab("musim");
                break;

            case "season":
                if (!args.isEmpty()) {
                    handleSeasonFilterCommand(parts);
                } else {
                    showCommandOutput("> tatap$ Gunakan format: :season <winter|spring|summer|fall> <tahun>", true);
                    Toast.makeText(this, "Format: :season <winter|spring|summer|fall> <tahun> (Contoh: :season fall 2024)", Toast.LENGTH_LONG).show();
                }
                break;

            case "airing":
            case "terbaru":
                resetFiltersToTab("airing");
                break;

            case "katalog":
            case "catalog":
                resetFiltersToTab("katalog");
                break;

            case "jadwal":
            case "schedule":
                if (!args.isEmpty()) {
                    String d = parseScheduleDayArg(args);
                    if (d != null) currentScheduleDay = d;
                } else {
                    currentScheduleDay = "today";
                }
                resetFiltersToTab("jadwal");
                break;

            case "genre":
                if (args.isEmpty() || args.equalsIgnoreCase("list") || args.equalsIgnoreCase("--list")) {
                    showGenreSelectorDialog();
                } else {
                    setGenreFilter(args);
                }
                break;

            case "filter":
                showCommandOutput("> tatap$ :filter [Membuka Filter Katalog]", false);
                showCatalogFilterDialog();
                break;

            case "cari":
            case "search":
                if (!args.isEmpty()) {
                    currentView = "cari";
                    currentSearchQuery = args;
                    currentPage = 1;
                    totalPages = 1;
                    hasNextPage = false;
                    hasPagingInfo = false;
                    updateTabButtons();
                    updateActiveFilterBar();
                    showCommandOutput("> tatap$ :cari \"" + args + "\" [Mencari...]", false);
                    fetchData();
                } else {
                    showCommandOutput("> tatap$ :cari [Gagal: Butuh kata kunci judul]", true);
                    Toast.makeText(this, "Gunakan: :cari <judul>", Toast.LENGTH_SHORT).show();
                }
                break;

            case "page":
            case "hal":
                try {
                    int p = Integer.parseInt(args);
                    if (p >= 1) {
                        currentPage = p;
                        showCommandOutput("> tatap$ :page " + p + " [Lompat ke Halaman " + p + "]", false);
                        fetchData();
                    }
                } catch (Exception e) {
                    showCommandOutput("> tatap$ :page [Gagal: Masukkan nomor halaman yang valid]", true);
                }
                break;

            case "source":
            case "switch":
                switchDefaultSource(args);
                break;

            case "ping":
            case "status":
                checkBackendStatus();
                break;

            case "clear":
            case "reset":
                resetFiltersToTab("musim");
                break;

            case "ai":
            case "aitranslate":
                showAiSettingsDialog();
                break;

            case "apikey":
            case "ollama":
            case "groq":
            case "gemini":
            case "openai":
            case "model":
            case "apiurl":
                cmdTranslateSetting(cmd, args);
                break;

            case "riwayat":
            case "history":
            case "lanjutan":
                if (args.equalsIgnoreCase("clear") || args.equalsIgnoreCase("hapus") || args.equalsIgnoreCase("reset")) {
                    clearWatchHistory();
                } else {
                    resetFiltersToTab("riwayat");
                }
                break;

            case "favorit":
            case "bookmark":
            case "bookmarks":
                switchView("favorit");
                showCommandOutput("> tatap$ :favorit [Menampilkan Anime Favorit]", false);
                break;

            case "logs":
            case "translog":
                showTranslateLogsDialog();
                break;

            case "update":
            case "upgrade":
                checkForUpdates(true);
                break;

            case "haptic":
            case "getar":
                handleHapticCommand(args);
                break;

            default:
                showCommandOutput("> tatap$ Perintah tidak dikenal: :" + cmd + " (Ketik :help)", true);
                break;
        }
    }

    private void handleHapticCommand(String args) {
        SharedPreferences sp = getSharedPreferences("tatap_player_prefs", MODE_PRIVATE);
        String trimmed = (args != null) ? args.trim().toLowerCase() : "";

        if (trimmed.startsWith("scene") || trimmed.startsWith("adegan")) {
            String sceneSub = trimmed.replaceFirst("^(scene|adegan)\\s*", "");
            boolean currentScene = sp.getBoolean("pref_scene_haptic", false);
            boolean targetScene;
            if ("on".equals(sceneSub) || "aktif".equals(sceneSub) || "1".equals(sceneSub)) {
                targetScene = true;
            } else if ("off".equals(sceneSub) || "mati".equals(sceneSub) || "0".equals(sceneSub)) {
                targetScene = false;
            } else {
                targetScene = !currentScene;
            }
            sp.edit().putBoolean("pref_scene_haptic", targetScene).apply();
            if (targetScene && btnToggleMenu != null) {
                HapticHelper.performHeavyClick(btnToggleMenu);
            }
            String stScene = targetScene ? "AKTIF" : "MATI";
            showCommandOutput("> tatap$ :haptic scene " + (targetScene ? "on" : "off") + " [Getaran Adegan Audio: " + stScene + "]", false);
            Toast.makeText(this, "Getaran Adegan Audio: " + (targetScene ? "Aktif" : "Mati"), Toast.LENGTH_SHORT).show();
            return;
        }

        if ("status".equals(trimmed)) {
            boolean uiHaptic = sp.getBoolean("pref_general_haptic", sp.getBoolean("pref_haptic", true));
            boolean sceneHaptic = sp.getBoolean("pref_scene_haptic", false);
            showCommandOutput("> tatap$ [STATUS HAPTIK] UI: " + (uiHaptic ? "AKTIF" : "MATI") + " | Adegan Audio: " + (sceneHaptic ? "AKTIF" : "MATI"), false);
            return;
        }

        boolean current = sp.getBoolean("pref_general_haptic", sp.getBoolean("pref_haptic", true));
        boolean target;
        if ("on".equalsIgnoreCase(trimmed) || "aktif".equalsIgnoreCase(trimmed) || "1".equals(trimmed)) {
            target = true;
        } else if ("off".equalsIgnoreCase(trimmed) || "mati".equalsIgnoreCase(trimmed) || "0".equals(trimmed)) {
            target = false;
        } else {
            target = !current;
        }
        sp.edit().putBoolean("pref_general_haptic", target).putBoolean("pref_haptic", target).apply();
        if (target && btnToggleMenu != null) {
            HapticHelper.performHeavyClick(btnToggleMenu);
        }
        String statusStr = target ? "AKTIF" : "MATI";
        showCommandOutput("> tatap$ :haptic " + (target ? "on" : "off") + " [Getaran Sentuh UI: " + statusStr + "]", false);
        Toast.makeText(this, "Getaran Sentuh UI: " + (target ? "Aktif" : "Mati"), Toast.LENGTH_SHORT).show();
    }

    private void handleSeasonFilterCommand(String[] parts) {
        // Format: :season <winter|spring|summer|fall> [tahun]
        if (parts.length >= 2) {
            String sName = parts[1].toLowerCase();
            if (!sName.matches("^(winter|spring|summer|fall)$")) {
                showCommandOutput("> tatap$ Musim harus: winter, spring, summer, fall", true);
                Toast.makeText(this, "Musim valid: winter, spring, summer, fall. Contoh: :season fall 2024", Toast.LENGTH_LONG).show();
                return;
            }
            int sYear = 2024;
            if (parts.length >= 3) {
                try {
                    sYear = Integer.parseInt(parts[2]);
                } catch (Exception ignored) {}
            }
            currentView = "season_filter";
            currentSeasonName = sName;
            currentSeasonYear = sYear;
            currentPage = 1;
            updateTabButtons();
            updateActiveFilterBar();
            showCommandOutput("> tatap$ :season " + sName + " " + sYear + " [Filter Diterapkan]", false);
            fetchData();
        } else {
            showCommandOutput("> tatap$ Format: :season <winter|spring|summer|fall> <tahun>", true);
        }
    }

    private void setGenreFilter(String genreSlugOrTitle) {
        currentView = "genre";
        currentGenre = genreSlugOrTitle.toLowerCase().trim().replace(" ", "-");
        currentPage = 1;
        updateTabButtons();
        updateActiveFilterBar();
        showCommandOutput("> tatap$ :genre " + currentGenre + " [Filter Genre Aktif]", false);
        fetchData();
    }

    private void showGenreSelectorDialog() {
        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        dialog.setContentView(R.layout.dialog_genre_selector);
        setupDialogWindowBounds(dialog);

        EditText etFilter = dialog.findViewById(R.id.et_filter_genre);
        ProgressBar pbGenre = dialog.findViewById(R.id.pb_genre_loading);
        RecyclerView rvGenres = dialog.findViewById(R.id.rv_genres);
        Button btnClose = dialog.findViewById(R.id.btn_close_genre_dialog);
        Button btnDismiss = dialog.findViewById(R.id.btn_dismiss_genre);
        Button btnReset = dialog.findViewById(R.id.btn_reset_genre_filter);

        int genreSpan = getResources().getInteger(R.integer.genre_dialog_columns);
        rvGenres.setLayoutManager(new GridLayoutManager(this, genreSpan));
        GenreChipAdapter genreAdapter = new GenreChipAdapter((slug, title) -> {
            dialog.dismiss();
            setGenreFilter(slug);
        });
        rvGenres.setAdapter(genreAdapter);

        btnClose.setOnClickListener(v -> dialog.dismiss());
        btnDismiss.setOnClickListener(v -> dialog.dismiss());
        btnReset.setOnClickListener(v -> {
            dialog.dismiss();
            resetFiltersToTab("musim");
        });

        etFilter.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                genreAdapter.filter(s.toString());
            }
            @Override
            public void afterTextChanged(Editable s) {}
        });

        TvFocusHelper.attachFocusScale(btnClose, 1.1f, 4f);
        TvFocusHelper.attachFocusScale(btnDismiss, 1.05f, 4f);
        TvFocusHelper.attachFocusScale(btnReset, 1.05f, 4f);

        dialog.show();

        // Fetch genres from backend
        new Thread(() -> {
            List<GenreItem> list = new ArrayList<>();
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/genres").openConnection();
                conn.setConnectTimeout(6000);
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                reader.close();

                JSONObject res = new JSONObject(sb.toString());
                if (res.optBoolean("success")) {
                    JSONArray arr = res.getJSONObject("data").getJSONArray("list");
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject g = arr.getJSONObject(i);
                        String slug = g.optString("slug", "");
                        String title = g.optString("title", "");
                        if ("hentai".equalsIgnoreCase(slug) || title.toLowerCase().contains("hentai")) {
                            continue;
                        }
                        list.add(new GenreItem(title, slug));
                    }
                }
            } catch (Exception ignored) {}

            if (list.isEmpty()) {
                // Fallback genres
                String[] fallback = new String[]{"Action", "Adventure", "Comedy", "Drama", "Fantasy", "Horror", "Mystery", "Romance", "Sci-Fi", "Slice of Life", "Sports", "Supernatural", "Isekai", "Psychological", "Thriller", "Magic"};
                for (String f : fallback) {
                    list.add(new GenreItem(f, f.toLowerCase().replace(" ", "-")));
                }
            }

            runOnUiThread(() -> {
                pbGenre.setVisibility(View.GONE);
                genreAdapter.setData(list);
            });
        }).start();
    }

    private void showCatalogFilterDialog() {
        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        dialog.setContentView(R.layout.dialog_catalog_filter);
        setupDialogWindowBounds(dialog);

        final String[] tempSort = new String[]{filterCatalogSort};
        final String[] tempYear = new String[]{filterCatalogYear};
        final String[] tempSeason = new String[]{filterCatalogSeason};
        final String[] tempMonth = new String[]{filterCatalogMonth};
        final String[] tempType = new String[]{filterCatalogType};
        final String[] tempStatus = new String[]{filterCatalogStatus};

        interface ChipSelectAction {
            void onSelect(String val);
        }

        class ChipGroupHelper {
            void bind(int[] ids, String[] values, String current, ChipSelectAction action) {
                for (int i = 0; i < ids.length; i++) {
                    final int idx = i;
                    TextView chip = dialog.findViewById(ids[i]);
                    if (chip == null) continue;
                    boolean selected = values[i].equals(current);
                    chip.setBackgroundResource(selected ? R.drawable.bg_chip_selected : R.drawable.bg_tab_inactive);
                    chip.setTextColor(selected ? 0xFFFFFFFF : 0xFF8892B0);
                    if (chip.getCompoundDrawables()[0] != null) {
                        chip.setCompoundDrawableTintList(android.content.res.ColorStateList.valueOf(selected ? 0xFFFFFFFF : 0xFF8892B0));
                    }
                    chip.setOnClickListener(v -> {
                        for (int j = 0; j < ids.length; j++) {
                            TextView c = dialog.findViewById(ids[j]);
                            if (c != null) {
                                boolean nowSel = (j == idx);
                                c.setBackgroundResource(nowSel ? R.drawable.bg_chip_selected : R.drawable.bg_tab_inactive);
                                c.setTextColor(nowSel ? 0xFFFFFFFF : 0xFF8892B0);
                                if (c.getCompoundDrawables()[0] != null) {
                                    c.setCompoundDrawableTintList(android.content.res.ColorStateList.valueOf(nowSel ? 0xFFFFFFFF : 0xFF8892B0));
                                }
                            }
                        }
                        action.onSelect(values[idx]);
                    });
                    TvFocusHelper.attachFocusScale(chip, 1.05f, 3f);
                }
            }
        }
        ChipGroupHelper helper = new ChipGroupHelper();

        // 1. Sort
        int[] sortIds = new int[]{
            R.id.chip_sort_pop, R.id.chip_sort_score, R.id.chip_sort_latest,
            R.id.chip_sort_trending, R.id.chip_sort_az, R.id.chip_sort_fav
        };
        String[] sortVals = new String[]{"popularity", "score", "latest", "trending", "az", "most_favorite"};
        helper.bind(sortIds, sortVals, tempSort[0], val -> tempSort[0] = val);

        // 2. Year
        int[] yearIds = new int[]{
            R.id.chip_year_all, R.id.chip_year_2026, R.id.chip_year_2025, R.id.chip_year_2024,
            R.id.chip_year_2023, R.id.chip_year_2022, R.id.chip_year_2021, R.id.chip_year_2020,
            R.id.chip_year_2015_2019, R.id.chip_year_2010_2014, R.id.chip_year_2000_2009, R.id.chip_year_classic
        };
        String[] yearVals = new String[]{
            "", "2026", "2025", "2024", "2023", "2022", "2021", "2020",
            "2015-2019", "2010-2014", "2000-2009", "<2000"
        };
        helper.bind(yearIds, yearVals, tempYear[0], val -> tempYear[0] = val);

        // 3. Season
        int[] seasonIds = new int[]{
            R.id.chip_season_all, R.id.chip_season_spring, R.id.chip_season_summer,
            R.id.chip_season_fall, R.id.chip_season_winter
        };
        String[] seasonVals = new String[]{"", "spring", "summer", "fall", "winter"};
        helper.bind(seasonIds, seasonVals, tempSeason[0], val -> tempSeason[0] = val);

        // 4. Month
        int[] monthIds = new int[]{
            R.id.chip_month_all, R.id.chip_month_1, R.id.chip_month_2, R.id.chip_month_3,
            R.id.chip_month_4, R.id.chip_month_5, R.id.chip_month_6, R.id.chip_month_7,
            R.id.chip_month_8, R.id.chip_month_9, R.id.chip_month_10, R.id.chip_month_11, R.id.chip_month_12
        };
        String[] monthVals = new String[]{"", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"};
        helper.bind(monthIds, monthVals, tempMonth[0], val -> tempMonth[0] = val);

        // 5. Type
        int[] typeIds = new int[]{
            R.id.chip_type_all, R.id.chip_type_tv, R.id.chip_type_movie,
            R.id.chip_type_ova, R.id.chip_type_ona, R.id.chip_type_special
        };
        String[] typeVals = new String[]{"", "tv", "movie", "ova", "ona", "special"};
        helper.bind(typeIds, typeVals, tempType[0], val -> tempType[0] = val);

        // 6. Status
        int[] statusIds = new int[]{
            R.id.chip_status_all, R.id.chip_status_airing, R.id.chip_status_completed
        };
        String[] statusVals = new String[]{"", "releasing", "completed"};
        helper.bind(statusIds, statusVals, tempStatus[0], val -> tempStatus[0] = val);

        // Action Buttons
        View btnClose = dialog.findViewById(R.id.btn_close_catalog_dialog);
        View btnReset = dialog.findViewById(R.id.btn_reset_catalog_filter);
        View btnApply = dialog.findViewById(R.id.btn_apply_catalog_filter);

        if (btnClose != null) {
            btnClose.setOnClickListener(v -> dialog.dismiss());
            TvFocusHelper.attachFocusScale(btnClose, 1.1f, 4f);
        }

        if (btnReset != null) {
            btnReset.setOnClickListener(v -> {
                dialog.dismiss();
                resetCatalogFilterState();
                currentView = "katalog";
                updateTabButtons();
                updateActiveFilterBar();
                showCommandOutput("> tatap$ Filter katalog direset ke Terpopuler", false);
                fetchData();
            });
            TvFocusHelper.attachFocusScale(btnReset, 1.05f, 4f);
        }

        if (btnApply != null) {
            btnApply.setOnClickListener(v -> {
                dialog.dismiss();
                filterCatalogSort = tempSort[0];
                filterCatalogYear = tempYear[0];
                filterCatalogSeason = tempSeason[0];
                filterCatalogMonth = tempMonth[0];
                filterCatalogType = tempType[0];
                filterCatalogStatus = tempStatus[0];
                currentPage = 1;
                currentView = "katalog";
                updateTabButtons();
                updateActiveFilterBar();
                showCommandOutput("> tatap$ " + getCatalogFilterSummary() + " [Diterapkan]", false);
                fetchData();
            });
            TvFocusHelper.attachFocusScale(btnApply, 1.05f, 4f);
        }

        dialog.show();
    }

    private void showCommandHelpDialog() {
        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        dialog.setContentView(R.layout.dialog_command_help);
        setupDialogWindowBounds(dialog);

        Button btnClose = dialog.findViewById(R.id.btn_close_help_dialog);
        btnClose.setOnClickListener(v -> dialog.dismiss());

        dialog.findViewById(R.id.cmd_item_season).setOnClickListener(v -> {
            dialog.dismiss();
            etSearch.setText(":season fall 2024");
            etSearch.setSelection(etSearch.getText().length());
            etSearch.requestFocus();
            showCommandOutput("> tatap$ Silakan tentukan musim & tahun lalu tekan Enter", false);
        });

        dialog.findViewById(R.id.cmd_item_source).setOnClickListener(v -> {
            dialog.dismiss();
            switchDefaultSource("otakudesu");
        });

        dialog.findViewById(R.id.cmd_item_ping).setOnClickListener(v -> {
            dialog.dismiss();
            checkBackendStatus();
        });

        dialog.findViewById(R.id.cmd_item_ai).setOnClickListener(v -> {
            dialog.dismiss();
            showAiSettingsDialog();
        });

        dialog.findViewById(R.id.cmd_item_apikey).setOnClickListener(v -> {
            dialog.dismiss();
            cmdTranslateSetting("apikey", "");
        });

        dialog.findViewById(R.id.cmd_item_gemini).setOnClickListener(v -> {
            dialog.dismiss();
            etSearch.setText(":gemini ");
            etSearch.setSelection(8);
            etSearch.requestFocus();
            showCommandOutput("> tatap$ Masukkan API key Google AI Studio (AQ...) Anda", false);
        });

        dialog.findViewById(R.id.cmd_item_groq).setOnClickListener(v -> {
            dialog.dismiss();
            etSearch.setText(":groq ");
            etSearch.setSelection(6);
            etSearch.requestFocus();
            showCommandOutput("> tatap$ Masukkan API key Groq Cloud (gsk_...) Anda", false);
        });

        dialog.findViewById(R.id.cmd_item_ollama).setOnClickListener(v -> {
            dialog.dismiss();
            etSearch.setText(":ollama ");
            etSearch.setSelection(8);
            etSearch.requestFocus();
            showCommandOutput("> tatap$ Masukkan API key Ollama Cloud Anda", false);
        });

        dialog.findViewById(R.id.cmd_item_model).setOnClickListener(v -> {
            dialog.dismiss();
            cmdTranslateSetting("model", "");
        });

        dialog.findViewById(R.id.cmd_item_logs).setOnClickListener(v -> {
            dialog.dismiss();
            showTranslateLogsDialog();
        });

        View itemHaptic = dialog.findViewById(R.id.cmd_item_haptic);
        if (itemHaptic != null) {
            TextView tvBadge = dialog.findViewById(R.id.tv_haptic_badge);
            TextView tvDesc = dialog.findViewById(R.id.tv_haptic_desc);
            SharedPreferences sp = getSharedPreferences("tatap_player_prefs", MODE_PRIVATE);
            Runnable updateHapticUI = () -> {
                boolean isEnabled = sp.getBoolean("pref_general_haptic", sp.getBoolean("pref_haptic", true));
                if (tvBadge != null) {
                    tvBadge.setText(isEnabled ? "AKTIF" : "MATI");
                    tvBadge.setTextColor(isEnabled ? 0xFF38BDF8 : 0xFFEF4444);
                }
                if (tvDesc != null) {
                    tvDesc.setText("Umpan balik getaran sentuh UI (" + (isEnabled ? "AKTIF" : "MATI") + " - ketuk untuk beralih). Adegan audio: :haptic scene");
                }
            };
            updateHapticUI.run();

            itemHaptic.setOnClickListener(v -> {
                boolean current = sp.getBoolean("pref_general_haptic", sp.getBoolean("pref_haptic", true));
                boolean newHaptic = !current;
                sp.edit().putBoolean("pref_general_haptic", newHaptic).putBoolean("pref_haptic", newHaptic).apply();
                updateHapticUI.run();
                if (newHaptic) {
                    HapticHelper.performHeavyClick(v);
                }
                showCommandOutput("> tatap$ :haptic " + (newHaptic ? "on" : "off") + " [Getaran Sentuh UI: " + (newHaptic ? "AKTIF" : "MATI") + "]", false);
                Toast.makeText(this, "Getaran Sentuh UI: " + (newHaptic ? "Aktif" : "Mati"), Toast.LENGTH_SHORT).show();
            });
        }

        View itemUpdate = dialog.findViewById(R.id.cmd_item_update);
        if (itemUpdate != null) {
            itemUpdate.setOnClickListener(v -> {
                dialog.dismiss();
                checkForUpdates(true);
            });
        }

        View itemClear = dialog.findViewById(R.id.cmd_item_clear);
        if (itemClear != null) {
            itemClear.setOnClickListener(v -> {
                dialog.dismiss();
                resetFiltersToTab("musim");
            });
        }

        int[] cmdItemIds = new int[]{
            R.id.btn_close_help_dialog,
            R.id.cmd_item_season, R.id.cmd_item_source,
            R.id.cmd_item_ping, R.id.cmd_item_ai, R.id.cmd_item_apikey,
            R.id.cmd_item_gemini, R.id.cmd_item_groq, R.id.cmd_item_ollama,
            R.id.cmd_item_model, R.id.cmd_item_logs,
            R.id.cmd_item_haptic, R.id.cmd_item_update, R.id.cmd_item_clear
        };
        for (int id : cmdItemIds) {
            View item = dialog.findViewById(id);
            if (item != null) {
                TvFocusHelper.attachFocusScale(item, 1.05f, 4f);
            }
        }

        dialog.show();
    }

    private void checkForUpdates(boolean manualTrigger) {
        AppUpdateManager.getInstance().checkUpdate(this, (msg, isError) -> {
            showCommandOutput(msg, isError);
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == AppUpdateManager.REQUEST_CODE_INSTALL_PERMISSION) {
            AppUpdateManager.getInstance().onInstallPermissionResult(this);
        }
    }

    private String maskKey(String key) {
        if (key == null || key.isEmpty()) return "(kosong)";
        if (key.length() <= 10) return "****";
        int prefixLen = key.startsWith("AQ.") ? 6 : (key.length() > 14 ? 8 : 4);
        return key.substring(0, prefixLen) + "..." + key.substring(key.length() - 4);
    }

    private void cmdTranslateSetting(String cmd, String rawArgs) {
        String args = rawArgs != null ? rawArgs.trim() : "";
        if (cmd.equals("apikey") || cmd.equals("ollama") || cmd.equals("groq") || cmd.equals("gemini") || cmd.equals("openai")) {
            args = args.replaceAll("^[\"']|[\"']$", "").trim();
        }

        if (args.isEmpty()) {
            showCommandOutput("> tatap$ Membaca status AI Translate...", false);
            new Thread(() -> {
                try {
                    HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/settings").openConnection();
                    conn.setConnectTimeout(3000);
                    BufferedReader r = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = r.readLine()) != null) sb.append(line);
                    r.close();

                    JSONObject res = new JSONObject(sb.toString());
                    JSONObject d = res.optJSONObject("data");
                    if (d == null) d = res;
                    String key = d.optString("translate_apikey", "");
                    String model = d.optString("translate_model", "gemini-2.0-flash");
                    String url = d.optString("translate_apiurl", "https://generativelanguage.googleapis.com/v1beta/openai");

                    runOnUiThread(() -> {
                        String out = "> tatap$ [AI STATUS] apikey: " + maskKey(key) + " | model: " + model;
                        showCommandOutput(out, false);
                        showAiSettingsDialog();
                    });
                } catch (Exception e) {
                    runOnUiThread(() -> showCommandOutput("> tatap$ [ERROR] Gagal membaca setelan: " + e.getMessage(), true));
                }
            }).start();
            return;
        }

        if (args.equalsIgnoreCase("clear") || args.equalsIgnoreCase("reset")) {
            JSONObject body = new JSONObject();
            try {
                if (cmd.equals("model")) body.put("translate_model", "gemini-2.0-flash");
                else if (cmd.equals("apiurl")) body.put("translate_apiurl", "https://generativelanguage.googleapis.com/v1beta/openai");
                else body.put("translate_apikey", "");
            } catch (Exception ignored) {}

            saveAiSettingsAndReport(body, cmd + " direset ke default");
            return;
        }

        JSONObject body = new JSONObject();
        String extra = "";
        try {
            if (cmd.equals("model")) {
                body.put("translate_model", args);
                extra = " [model disetel ke " + args + "]";
            } else if (cmd.equals("apiurl")) {
                body.put("translate_apiurl", args);
                extra = " [apiurl disetel ke " + args + "]";
            } else {
                body.put("translate_apikey", args);
                boolean isOllama = cmd.equals("ollama") || args.startsWith("ollama_") || args.startsWith("ol_") || args.matches("^[a-f0-9]{32}\\.[A-Za-z0-9_-]+$");
                if (isOllama) {
                    body.put("translate_apiurl", "https://ollama.com/v1");
                    body.put("translate_model", "gpt-oss:20b");
                    extra = " [Auto: Ollama Cloud (gpt-oss:20b)]";
                } else if (cmd.equals("gemini") || args.startsWith("AQ.") || args.startsWith("AIza") || args.startsWith("AQ")) {
                    body.put("translate_apiurl", "https://generativelanguage.googleapis.com/v1beta/openai");
                    body.put("translate_model", "gemini-2.0-flash");
                    extra = " [Auto: Google AI Studio (gemini-2.0-flash)]";
                } else if (cmd.equals("groq") || args.startsWith("gsk_")) {
                    body.put("translate_apiurl", "https://api.groq.com/openai/v1");
                    body.put("translate_model", "llama-3.3-70b-versatile");
                    extra = " [Auto: Groq Cloud (llama-3.3-70b-versatile)]";
                } else if (args.startsWith("sk-or-")) {
                    body.put("translate_apiurl", "https://openrouter.ai/api/v1");
                    body.put("translate_model", "google/gemini-2.0-flash-exp:free");
                    extra = " [Auto: OpenRouter (gemini-2.0-flash-exp)]";
                } else if (cmd.equals("openai") || args.startsWith("sk-") || args.startsWith("sk_")) {
                    body.put("translate_apiurl", "https://api.openai.com/v1");
                    body.put("translate_model", "gpt-4o-mini");
                    extra = " [Auto: OpenAI (gpt-4o-mini)]";
                } else {
                    extra = " [Provider Custom]";
                }
            }
        } catch (Exception ignored) {}

        String masked = maskKey(args);
        saveAiSettingsAndReport(body, cmd + " disimpan (" + masked + ")" + extra);
    }

    private void saveAiSettingsAndReport(JSONObject payload, String successMsg) {
        new Thread(() -> {
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/settings").openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                conn.getOutputStream().write(payload.toString().getBytes("UTF-8"));
                conn.getInputStream().close();
                runOnUiThread(() -> {
                    showCommandOutput("> tatap$ [OK] " + successMsg, false);
                    Toast.makeText(this, successMsg, Toast.LENGTH_SHORT).show();
                });
            } catch (Exception e) {
                runOnUiThread(() -> showCommandOutput("> tatap$ [ERROR] Gagal menyimpan: " + e.getMessage(), true));
            }
        }).start();
    }

    private void showTranslateLogsDialog() {
        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        dialog.setContentView(R.layout.dialog_translate_logs);
        setupDialogWindowBounds(dialog);

        TextView tvLogs = dialog.findViewById(R.id.tv_translate_logs_content);
        Button btnClose = dialog.findViewById(R.id.btn_close_logs_dialog);
        Button btnDismiss = dialog.findViewById(R.id.btn_dismiss_logs);
        Button btnRefresh = dialog.findViewById(R.id.btn_refresh_logs);

        btnClose.setOnClickListener(v -> dialog.dismiss());
        btnDismiss.setOnClickListener(v -> dialog.dismiss());

        Runnable loadLogs = () -> {
            tvLogs.setText("Mengambil log terbaru dari server...");
            new Thread(() -> {
                try {
                    HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/translate/logs").openConnection();
                    conn.setConnectTimeout(3000);
                    BufferedReader r = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = r.readLine()) != null) sb.append(line);
                    r.close();

                    JSONObject res = new JSONObject(sb.toString());
                    JSONArray arr = res.getJSONObject("data").getJSONArray("logs");
                    StringBuilder logText = new StringBuilder();
                    for (int i = 0; i < arr.length(); i++) {
                        logText.append("• ").append(arr.getString(i)).append("\n\n");
                    }
                    if (arr.length() == 0) {
                        logText.append("(Belum ada aktivitas translasi subtitle yang tercatat)");
                    }
                    runOnUiThread(() -> tvLogs.setText(logText.toString().trim()));
                } catch (Exception e) {
                    runOnUiThread(() -> tvLogs.setText("Gagal membaca log: " + e.getMessage()));
                }
            }).start();
        };

        TvFocusHelper.attachFocusScale(btnClose, 1.1f, 4f);
        TvFocusHelper.attachFocusScale(btnDismiss, 1.05f, 4f);
        TvFocusHelper.attachFocusScale(btnRefresh, 1.05f, 4f);

        btnRefresh.setOnClickListener(v -> loadLogs.run());
        dialog.show();
        loadLogs.run();
    }

    private void showAiSettingsDialog() {
        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        dialog.setContentView(R.layout.dialog_ai_settings);
        setupDialogWindowBounds(dialog);

        TextView tvKey = dialog.findViewById(R.id.tv_ai_status_key);
        TextView tvModel = dialog.findViewById(R.id.tv_ai_status_model);
        TextView tvUrl = dialog.findViewById(R.id.tv_ai_status_url);
        EditText etKey = dialog.findViewById(R.id.et_ai_apikey);
        EditText etModel = dialog.findViewById(R.id.et_ai_model);
        EditText etUrl = dialog.findViewById(R.id.et_ai_apiurl);

        Button btnClose = dialog.findViewById(R.id.btn_close_ai_dialog);
        Button btnSave = dialog.findViewById(R.id.btn_ai_save);
        Button btnReset = dialog.findViewById(R.id.btn_ai_reset_key);
        Button btnLogs = dialog.findViewById(R.id.btn_ai_view_logs);

        Button btnPresetGemini = dialog.findViewById(R.id.btn_preset_gemini);
        Button btnPresetGroq = dialog.findViewById(R.id.btn_preset_groq);
        Button btnPresetOllama = dialog.findViewById(R.id.btn_preset_ollama);
        Button btnPresetOpenAI = dialog.findViewById(R.id.btn_preset_openai);

        btnClose.setOnClickListener(v -> dialog.dismiss());

        etKey.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                String k = s.toString().trim();
                if (k.startsWith("gsk_")) {
                    etModel.setText("llama-3.3-70b-versatile");
                    etUrl.setText("https://api.groq.com/openai/v1");
                    tvKey.setText("API Key : " + maskKey(k) + " (Groq Cloud)");
                } else if (k.startsWith("AQ.") || k.startsWith("AIza") || k.startsWith("AQ")) {
                    etModel.setText("gemini-2.0-flash");
                    etUrl.setText("https://generativelanguage.googleapis.com/v1beta/openai");
                    tvKey.setText("API Key : " + maskKey(k) + " (Google AI Studio)");
                } else if (k.startsWith("sk-or-")) {
                    etModel.setText("google/gemini-2.0-flash-exp:free");
                    etUrl.setText("https://openrouter.ai/api/v1");
                    tvKey.setText("API Key : " + maskKey(k) + " (OpenRouter)");
                } else if (k.startsWith("ollama_") || k.startsWith("ol_") || (k.length() > 35 && k.contains("."))) {
                    etModel.setText("gpt-oss:20b");
                    etUrl.setText("https://ollama.com/v1");
                    tvKey.setText("API Key : " + maskKey(k) + " (Ollama Cloud)");
                } else if (k.startsWith("sk-") || k.startsWith("sk_")) {
                    etModel.setText("gpt-4o-mini");
                    etUrl.setText("https://api.openai.com/v1");
                    tvKey.setText("API Key : " + maskKey(k) + " (OpenAI)");
                }
            }
            @Override
            public void afterTextChanged(Editable s) {}
        });

        btnLogs.setOnClickListener(v -> {
            dialog.dismiss();
            showTranslateLogsDialog();
        });

        btnPresetGemini.setOnClickListener(v -> {
            etModel.setText("gemini-2.0-flash");
            etUrl.setText("https://generativelanguage.googleapis.com/v1beta/openai");
            etKey.setHint("Tempel kunci Google AI (AQ...)");
            Toast.makeText(this, "Preset Google Gemini dipilih", Toast.LENGTH_SHORT).show();
        });

        btnPresetGroq.setOnClickListener(v -> {
            etModel.setText("llama-3.3-70b-versatile");
            etUrl.setText("https://api.groq.com/openai/v1");
            etKey.setHint("Tempel kunci Groq Cloud (gsk_...)");
            Toast.makeText(this, "Preset Groq Cloud dipilih", Toast.LENGTH_SHORT).show();
        });

        btnPresetOllama.setOnClickListener(v -> {
            etModel.setText("gpt-oss:20b");
            etUrl.setText("https://ollama.com/v1");
            etKey.setHint("Tempel kunci Ollama Cloud");
            Toast.makeText(this, "Preset Ollama Cloud dipilih", Toast.LENGTH_SHORT).show();
        });

        btnPresetOpenAI.setOnClickListener(v -> {
            etModel.setText("gpt-4o-mini");
            etUrl.setText("https://api.openai.com/v1");
            etKey.setHint("Tempel kunci OpenAI (sk-...)");
            Toast.makeText(this, "Preset OpenAI dipilih", Toast.LENGTH_SHORT).show();
        });

        btnReset.setOnClickListener(v -> {
            dialog.dismiss();
            cmdTranslateSetting("apikey", "reset");
        });

        btnSave.setOnClickListener(v -> {
            String newKey = etKey.getText().toString().trim();
            String newModel = etModel.getText().toString().trim();
            String newUrl = etUrl.getText().toString().trim();

            JSONObject payload = new JSONObject();
            try {
                if (!newKey.isEmpty()) payload.put("translate_apikey", newKey);
                if (!newModel.isEmpty()) payload.put("translate_model", newModel);
                if (!newUrl.isEmpty()) payload.put("translate_apiurl", newUrl);
            } catch (Exception ignored) {}

            dialog.dismiss();
            saveAiSettingsAndReport(payload, "Pengaturan AI Translate disimpan");
        });

        // Fetch current settings
        new Thread(() -> {
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/settings").openConnection();
                conn.setConnectTimeout(3000);
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
                String u = d.optString("translate_apiurl", "https://generativelanguage.googleapis.com/v1beta/openai");

                runOnUiThread(() -> {
                    tvKey.setText("API Key : " + maskKey(k));
                    tvModel.setText("Model   : " + m);
                    tvUrl.setText("API URL : " + u);
                    etModel.setText(m);
                    etUrl.setText(u);
                });
            } catch (Exception ignored) {}
        }).start();

        TvFocusHelper.attachFocusScale(btnClose, 1.1f, 4f);
        TvFocusHelper.attachFocusScale(btnSave, 1.05f, 4f);
        TvFocusHelper.attachFocusScale(btnReset, 1.05f, 4f);
        TvFocusHelper.attachFocusScale(btnLogs, 1.05f, 4f);
        TvFocusHelper.attachFocusScale(btnPresetGemini, 1.05f, 4f);
        TvFocusHelper.attachFocusScale(btnPresetGroq, 1.05f, 4f);
        TvFocusHelper.attachFocusScale(btnPresetOllama, 1.05f, 4f);
        TvFocusHelper.attachFocusScale(btnPresetOpenAI, 1.05f, 4f);

        dialog.show();
    }

    private void switchDefaultSource(String target) {
        String s = target.toLowerCase().trim();
        String newSrc = s.contains("otaku") ? "otakudesu" : "hianime";

        showCommandOutput("> tatap$ :source " + newSrc + " [Mengalihkan sumber...]", false);

        new Thread(() -> {
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/settings").openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                JSONObject body = new JSONObject();
                body.put("preferred_source", newSrc);
                conn.getOutputStream().write(body.toString().getBytes("UTF-8"));
                conn.getInputStream().close();
                runOnUiThread(() -> {
                    String label = newSrc.equals("otakudesu") ? "Otakudesu (Sub Indo)" : "HiAnime (Multi-Sub)";
                    showCommandOutput("> tatap$ [OK] Sumber default berhasil diubah ke " + label, false);
                    fetchData();
                });
            } catch (Exception e) {
                runOnUiThread(() -> showCommandOutput("> tatap$ [ERROR] Gagal ubah sumber: " + e.getMessage(), true));
            }
        }).start();
    }

    private void checkBackendStatus() {
        showCommandOutput("> tatap$ :ping [Memeriksa 127.0.0.1:8767...]", false);
        updateBackendStatusUI(0);
        new Thread(() -> {
            try {
                long start = System.currentTimeMillis();
                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/ping").openConnection();
                conn.setConnectTimeout(2000);
                int code = conn.getResponseCode();
                long elapsed = System.currentTimeMillis() - start;
                conn.disconnect();
                runOnUiThread(() -> {
                    if (code == 200) {
                        updateBackendStatusUI(1);
                        showCommandOutput("> tatap$ [PONG] Backend ONLINE (127.0.0.1:8767 OK, " + elapsed + "ms)", false);
                    } else {
                        updateBackendStatusUI(2);
                        showCommandOutput("> tatap$ [WARN] Backend responded HTTP " + code, true);
                    }
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    updateBackendStatusUI(2);
                    showCommandOutput("> tatap$ [OFFLINE] Backend tidak terhubung: " + e.getMessage(), true);
                });
            }
        }).start();
    }

    private void switchView(String targetView) {
        currentView = targetView;
        currentPage = 1;
        totalPages = 1;
        hasNextPage = false;
        hasPagingInfo = false;
        updateTabButtons();
        updateActiveFilterBar();
        fetchData();
    }

    private void setTabAppearance(TextView tab, boolean active) {
        if (tab == null) return;
        boolean isVerticalSidebar = (layoutTabsContainer != null && layoutTabsContainer.getOrientation() == LinearLayout.VERTICAL);
        if (isVerticalSidebar) {
            tab.setBackgroundResource(R.drawable.bg_tv_sidebar_item);
            tab.setSelected(active);
        } else {
            tab.setBackgroundResource(active ? R.drawable.bg_tab_active : R.drawable.bg_tab_inactive);
        }
        int color = active ? 0xFFFFFFFF : 0xFFA1A1A6;
        tab.setTextColor(color);
        if (TvFocusHelper.isTv(this) && !isVerticalSidebar) {
            updateTvTabSpannable(tab, active);
        } else {
            tab.setCompoundDrawableTintList(android.content.res.ColorStateList.valueOf(color));
        }
        if (isVerticalSidebar) {
            tab.setText(isTvSidebarExpanded ? getTabTitleString(tab) : "");
            tab.setGravity(isTvSidebarExpanded ? (Gravity.CENTER_VERTICAL | Gravity.START) : Gravity.CENTER);
            tab.setPadding(isTvSidebarExpanded ? dpToPx(10) : 0, 0, isTvSidebarExpanded ? dpToPx(10) : 0, 0);
        }
    }

    private int getTabIconRes(TextView tab) {
        if (tab == null) return 0;
        int id = tab.getId();
        if (id == R.id.btn_tab_musim) return R.drawable.ic_tab_season;
        if (id == R.id.btn_tab_airing) return R.drawable.ic_tab_airing;
        if (id == R.id.btn_tab_jadwal) return R.drawable.ic_tab_schedule;
        if (id == R.id.btn_tab_riwayat) return R.drawable.ic_tab_history;
        if (id == R.id.btn_tab_favorit) return R.drawable.ic_tab_favorite;
        if (id == R.id.btn_tab_katalog) return R.drawable.ic_tab_catalog;
        if (id == R.id.btn_tab_genre) return R.drawable.ic_tab_genre;
        return 0;
    }

    private String getTabTitleString(TextView tab) {
        if (tab == null) return "";
        int id = tab.getId();
        if (id == R.id.btn_tab_musim) return "Musim Ini";
        if (id == R.id.btn_tab_airing) return "Masih Tayang";
        if (id == R.id.btn_tab_jadwal) return "Jadwal";
        if (id == R.id.btn_tab_riwayat) return "Riwayat";
        if (id == R.id.btn_tab_favorit) return "Favorit";
        if (id == R.id.btn_tab_katalog) return "Katalog";
        if (id == R.id.btn_tab_genre) return "Genre";
        CharSequence txt = tab.getText();
        return txt != null ? txt.toString().trim() : "";
    }

    private void updateTvTabSpannable(TextView tab, boolean active) {
        if (tab == null) return;
        int iconRes = getTabIconRes(tab);
        String title = getTabTitleString(tab);
        if (iconRes == 0 || title.isEmpty()) return;

        Drawable icon = ContextCompat.getDrawable(this, iconRes);
        if (icon == null) return;

        icon = DrawableCompat.wrap(icon.mutate());
        int tint = active ? 0xFFFFFFFF : 0xFF8892B0;
        DrawableCompat.setTint(icon, tint);

        int iconSize = dpToPx(16);
        icon.setBounds(0, 0, iconSize, iconSize);

        String fullText = "   " + title;
        SpannableString ss = new SpannableString(fullText);
        ss.setSpan(new TvFocusHelper.CenteredImageSpan(icon), 0, 1, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE);

        tab.setText(ss);
    }

    private void updateTabButtons() {
        boolean isMusim = "musim".equals(currentView);
        boolean isAiring = "airing".equals(currentView);
        boolean isJadwal = "jadwal".equals(currentView);
        boolean isRiwayat = "riwayat".equals(currentView);
        boolean isFavorit = "favorit".equals(currentView);
        boolean isKatalog = "katalog".equals(currentView);
        boolean isGenre = "genre".equals(currentView);

        setTabAppearance(btnTabMusim, isMusim);
        setTabAppearance(btnTabAiring, isAiring);
        setTabAppearance(btnTabJadwal, isJadwal);
        setTabAppearance(btnTabRiwayat, isRiwayat);
        setTabAppearance(btnTabFavorit, isFavorit);
        setTabAppearance(btnTabKatalog, isKatalog);
        setTabAppearance(btnTabGenre, isGenre);

        if (btnTabJadwal != null && TvFocusHelper.isTv(this)) {
            boolean isVerticalSidebar = (layoutTabsContainer != null && layoutTabsContainer.getOrientation() == LinearLayout.VERTICAL);
            if (isVerticalSidebar) {
                btnTabJadwal.setNextFocusDownId(R.id.btn_tab_riwayat);
                btnTabJadwal.setNextFocusRightId(isJadwal ? R.id.btn_day_senin : R.id.rv_anime_grid);
            } else {
                btnTabJadwal.setNextFocusDownId(isJadwal ? R.id.btn_day_senin : R.id.rv_anime_grid);
            }
        }

        if (layoutScheduleDays != null) {
            layoutScheduleDays.setVisibility(isJadwal ? View.VISIBLE : View.GONE);
            if (isJadwal) {
                updateScheduleDayButtons();
            }
        }

        if (btnHeaderHistory != null) {
            btnHeaderHistory.setTextColor(isRiwayat ? 0xFF38BDF8 : 0xFF94A3B8);
        }
    }

    private void switchScheduleDay(String day) {
        currentScheduleDay = day;
        updateScheduleDayButtons();
        fetchData();
    }

    private void updateScheduleDayButtons() {
        TextView[] chips = {btnDaySenin, btnDaySelasa, btnDayRabu, btnDayKamis, btnDayJumat, btnDaySabtu, btnDayMinggu};
        String[] keys = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"};
        String activeKey = currentScheduleDay;
        if ("today".equals(activeKey) && !currentScheduleActualDay.isEmpty()) {
            activeKey = currentScheduleActualDay;
        }

        TextView activeChip = null;
        for (int i = 0; i < chips.length; i++) {
            TextView chip = chips[i];
            if (chip == null) continue;
            boolean isActive = keys[i].equalsIgnoreCase(activeKey);
            chip.setBackgroundResource(isActive ? R.drawable.bg_tab_active : R.drawable.bg_header_button);
            chip.setTextColor(isActive ? 0xFFFFFFFF : 0xFF8892B0);
            if (isActive) activeChip = chip;
        }

        if (activeChip != null && layoutScheduleDays instanceof HorizontalScrollView) {
            final TextView target = activeChip;
            layoutScheduleDays.post(() -> {
                int scrollX = target.getLeft() - dpToPx(20);
                ((HorizontalScrollView) layoutScheduleDays).smoothScrollTo(Math.max(0, scrollX), 0);
            });
        }
    }

    private String getScheduleDayLabel(String key) {
        if (key == null) return "Hari Ini";
        switch (key.toLowerCase()) {
            case "monday": case "senin": return "Senin";
            case "tuesday": case "selasa": return "Selasa";
            case "wednesday": case "rabu": return "Rabu";
            case "thursday": case "kamis": return "Kamis";
            case "friday": case "jumat": return "Jumat";
            case "saturday": case "sabtu": return "Sabtu";
            case "sunday": case "minggu": return "Minggu";
            case "yesterday": case "kemarin": return "Kemarin";
            case "tomorrow": case "besok": return "Besok";
            default: return "Hari Ini";
        }
    }

    private String parseScheduleDayArg(String arg) {
        if (arg == null) return "today";
        String a = arg.trim().toLowerCase();
        switch (a) {
            case "senin": case "mon": case "monday": return "monday";
            case "selasa": case "tue": case "tuesday": return "tuesday";
            case "rabu": case "wed": case "wednesday": return "wednesday";
            case "kamis": case "thu": case "thursday": return "thursday";
            case "jumat": case "fri": case "friday": return "friday";
            case "sabtu": case "sat": case "saturday": return "saturday";
            case "minggu": case "sun": case "sunday": return "sunday";
            case "kemarin": case "yesterday": return "yesterday";
            case "besok": case "tomorrow": return "tomorrow";
            case "hari ini": case "today": default: return "today";
        }
    }

    private void activateSearchInput() {
        if (etSearch == null) return;
        etSearch.setFocusable(true);
        etSearch.setFocusableInTouchMode(true);
        etSearch.requestFocus();
        showKeyboard();
    }

    private void showKeyboard() {
        if (etSearch == null) return;
        etSearch.post(() -> {
            InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
            if (imm != null) {
                imm.showSoftInput(etSearch, InputMethodManager.SHOW_FORCED);
            }
        });
    }

    private void hideKeyboard() {
        if (etSearch == null) return;
        InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
        if (imm != null) {
            imm.hideSoftInputFromWindow(etSearch.getWindowToken(), 0);
        }
    }

    private void startEmbeddedBackend() {
        new Thread(() -> {
            try {
                Log.d(TAG, "Mencoba menyalakan Chaquopy Python Runtime...");
                Class<?> pyClass = Class.forName("com.chaquo.python.Python");
                if (!(Boolean) pyClass.getMethod("isStarted").invoke(null)) {
                    Class<?> androidPlatform = Class.forName("com.chaquo.python.android.AndroidPlatform");
                    Object platform = androidPlatform.getConstructor(Context.class).newInstance(getApplicationContext());
                    pyClass.getMethod("start", Class.forName("com.chaquo.python.Platform")).invoke(null, platform);
                }
                Object pyInstance = pyClass.getMethod("getInstance").invoke(null);
                Object launcherMod = pyClass.getMethod("getModule", String.class).invoke(pyInstance, "server_launcher");
                boolean isTv = TvFocusHelper.isTv(this);
                String dataDir = getFilesDir().getAbsolutePath();
                Log.d(TAG, "Menjalankan server_launcher.py dengan dataDir=" + dataDir + ", isTv=" + isTv);
                launcherMod.getClass().getMethod("callAttr", String.class, Object[].class).invoke(launcherMod, "run_in_background", new Object[]{dataDir, isTv});
                Log.d(TAG, "server_launcher.run_in_background dipanggil dengan sukses.");
            } catch (Throwable t) {
                Log.e(TAG, "Error startEmbeddedBackend: " + t.getMessage(), t);
                runOnUiThread(() -> {
                    showCommandOutput("> tatap$ Gagal start backend: " + t.getMessage(), true);
                });
            }
        }).start();
    }

    private void waitForServerAndLoadCatalog(final int attempt) {
        new Thread(() -> {
            boolean ready = false;
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/ping").openConnection();
                conn.setConnectTimeout(800);
                conn.setReadTimeout(800);
                ready = (conn.getResponseCode() == 200);
                conn.disconnect();
            } catch (Exception ignored) {}

            final boolean isReady = ready;
            if (isReady) {
                runOnUiThread(() -> {
                    updateBackendStatusUI(1);
                    fetchData();
                });
            } else if (attempt < 45) { // Coba sampai ~22 detik
                runOnUiThread(() -> {
                    if (attempt % 5 == 0 && attempt > 0) {
                        updateBackendStatusUI(0);
                    }
                });
                try { Thread.sleep(500); } catch (Exception ignored) {}
                waitForServerAndLoadCatalog(attempt + 1);
            } else {
                runOnUiThread(() -> {
                    updateBackendStatusUI(2);
                    showCommandOutput("> tatap$ Server butuh inisialisasi lebih lama. Ketuk badge status untuk mencoba ulang.", true);
                    if (btnStatusPower != null) {
                        btnStatusPower.setOnClickListener(v -> {
                            updateBackendStatusUI(0);
                            startEmbeddedBackend();
                            waitForServerAndLoadCatalog(0);
                        });
                    }
                    fetchData();
                });
            }
        }).start();
    }

    private void fetchData() {
        if (pbLoading != null) pbLoading.setVisibility(View.VISIBLE);
        if (tvPageIndicator != null) {
            if (totalPages > 1) {
                tvPageIndicator.setText("Hal " + currentPage + " / " + totalPages);
            } else {
                tvPageIndicator.setText("Hal " + currentPage);
            }
        }
        btnPrevPage.setEnabled(currentPage > 1);
        btnPrevPage.setAlpha(currentPage > 1 ? 1.0f : 0.4f);

        String title;
        String endpoint;

        if ("musim".equals(currentView)) {
            title = "Tayang Musim Ini (Hal " + currentPage + ")";
            endpoint = "/api/seasonal?which=now&page=" + currentPage;
        } else if ("airing".equals(currentView)) {
            title = "Masih Tayang (Hal " + currentPage + ")";
            endpoint = "/api/seasonal?which=airing&page=" + currentPage;
        } else if ("katalog".equals(currentView)) {
            if (isCatalogFilterActive()) {
                StringBuilder ep = new StringBuilder("/api/browse?sort=").append(URLEncoder.encode(filterCatalogSort));
                if (!filterCatalogYear.isEmpty()) ep.append("&year=").append(URLEncoder.encode(filterCatalogYear));
                if (!filterCatalogSeason.isEmpty()) ep.append("&season=").append(URLEncoder.encode(filterCatalogSeason));
                if (!filterCatalogMonth.isEmpty()) ep.append("&month=").append(URLEncoder.encode(filterCatalogMonth));
                if (!filterCatalogType.isEmpty()) ep.append("&type=").append(URLEncoder.encode(filterCatalogType));
                if (!filterCatalogStatus.isEmpty()) ep.append("&status=").append(URLEncoder.encode(filterCatalogStatus));
                ep.append("&page=").append(currentPage);
                endpoint = ep.toString();
                title = "Katalog Filter (Hal " + currentPage + ")";
            } else {
                title = "Katalog Populer (Hal " + currentPage + ")";
                endpoint = "/api/catalog?page=" + currentPage;
            }
        } else if ("jadwal".equals(currentView)) {
            String dayLabel = getScheduleDayLabel(currentScheduleDay);
            title = "Jadwal Rilis (" + dayLabel + ")";
            endpoint = "/api/schedule?day=" + currentScheduleDay;
        } else if ("genre".equals(currentView)) {
            title = "Genre: " + currentGenre.toUpperCase().replace("-", " ") + " (Hal " + currentPage + ")";
            endpoint = "/api/browse?genre=" + URLEncoder.encode(currentGenre) + "&page=" + currentPage;
        } else if ("season_filter".equals(currentView)) {
            title = "Musim: " + currentSeasonName.toUpperCase() + " " + currentSeasonYear + " (Hal " + currentPage + ")";
            endpoint = "/api/seasonal?season=" + URLEncoder.encode(currentSeasonName) + "&year=" + currentSeasonYear + "&page=" + currentPage;
        } else if ("riwayat".equals(currentView)) {
            title = "Riwayat Tontonan";
            endpoint = "/api/history";
        } else if ("favorit".equals(currentView)) {
            title = "Anime Favorit";
            endpoint = "/api/bookmarks";
        } else {
            title = "Hasil Pencarian: " + currentSearchQuery + (currentPage > 1 ? " (Hal " + currentPage + ")" : "");
            endpoint = "/api/search?q=" + URLEncoder.encode(currentSearchQuery) + "&page=" + currentPage + "&limit=24";
        }

        tvSectionTitle.setText(title);
        if (layoutPagination != null) {
            layoutPagination.setVisibility("riwayat".equals(currentView) || "jadwal".equals(currentView) || "favorit".equals(currentView) ? View.GONE : View.VISIBLE);
        }

        final String cacheKey = currentView + ":" + currentPage + ":" + currentGenre + ":" + currentSeasonName + ":" + currentSeasonYear + ":" + currentScheduleDay + ":" + filterCatalogSort + ":" + filterCatalogYear + ":" + filterCatalogSeason + ":" + filterCatalogMonth + ":" + filterCatalogType + ":" + filterCatalogStatus;
        final boolean canCache = !"cari".equals(currentView) && !"riwayat".equals(currentView) && !"favorit".equals(currentView);

        // 1. Cek In-Memory Cache untuk peralihan instan (<1ms)
        if (canCache && (swipeRefreshLayout == null || !swipeRefreshLayout.isRefreshing())) {
            TabCacheEntry cached = tabDataCache.get(cacheKey);
            if (cached != null && !cached.isExpired()) {
                totalPages = cached.totalPages;
                hasNextPage = cached.hasNextPage;
                hasPagingInfo = cached.hasPagingInfo;
                renderAnimeData(cached.items, cached.count);
                return;
            }
        }

        // 2. Aktifkan animasi pemuatan data
        showLoadingState("Memuat " + title + "...");

        final int fetchToken = currentFetchToken.incrementAndGet();

        new Thread(() -> {
            try {
                String u = "http://127.0.0.1:8767" + endpoint;
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setConnectTimeout(12000);
                conn.setReadTimeout(15000);
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                reader.close();

                // Abaikan jika token sudah tidak mutakhir (mencegah race condition antar-tab)
                if (fetchToken != currentFetchToken.get()) {
                    return;
                }

                JSONObject res = new JSONObject(sb.toString());
                if (res.optBoolean("success")) {
                    JSONArray arr = res.optJSONArray("data");
                    JSONObject dataObj = res.optJSONObject("data");
                    if (arr == null && dataObj != null) {
                        arr = dataObj.optJSONArray("results");
                        if (arr == null) arr = dataObj.optJSONArray("items");
                    }
                    if (arr == null) arr = new JSONArray();

                    List<JSONObject> list = new ArrayList<>();
                    for (int i = 0; i < arr.length(); i++) {
                        list.add(arr.getJSONObject(i));
                    }

                    final int count = list.size();

                    int extractedTotalPages = 1;
                    boolean extractedHasNext = false;
                    boolean extractedHasPagingInfo = false;
                    if (dataObj != null) {
                        if (dataObj.has("total_pages")) {
                            extractedTotalPages = dataObj.optInt("total_pages", 1);
                            extractedHasPagingInfo = true;
                        }
                        if (dataObj.has("has_next")) {
                            extractedHasNext = dataObj.optBoolean("has_next", false);
                            extractedHasPagingInfo = true;
                        }
                    }
                    totalPages = extractedTotalPages;
                    hasNextPage = extractedHasNext;
                    hasPagingInfo = extractedHasPagingInfo;

                    if ("jadwal".equals(currentView)) {
                        if (dataObj != null) {
                            String curDay = dataObj.optString("current_day", "");
                            String dayName = dataObj.optString("day_name", "");
                            boolean isToday = dataObj.optBoolean("is_today", false);
                            if (!curDay.isEmpty()) currentScheduleActualDay = curDay;
                            runOnUiThread(() -> {
                                if (!dayName.isEmpty()) {
                                    tvSectionTitle.setText("Jadwal Rilis (" + dayName + (isToday ? " · Hari Ini" : "") + ")");
                                }
                                updateScheduleDayButtons();
                            });
                        }
                    }

                    if (canCache) {
                        tabDataCache.put(cacheKey, new TabCacheEntry(list, count, totalPages, hasNextPage, hasPagingInfo));
                    }

                    runOnUiThread(() -> {
                        if (fetchToken != currentFetchToken.get()) return;
                        renderAnimeData(list, count);
                    });
                } else {
                    final String err = res.optString("error", "gagal memuat data");
                    runOnUiThread(() -> {
                        if (fetchToken != currentFetchToken.get()) return;
                        if (layoutLoadingState != null) layoutLoadingState.setVisibility(View.GONE);
                        if (pbLoading != null) pbLoading.setVisibility(View.GONE);
                        if (swipeRefreshLayout != null) swipeRefreshLayout.setRefreshing(false);
                        if (rvGrid != null) rvGrid.setAlpha(1.0f);
                        showCommandOutput("> tatap$ [ERROR] " + err, true);
                        if (adapter.getItemCount() == 0) {
                            if (layoutPagination != null) layoutPagination.setVisibility(View.GONE);
                            if (layoutEmptyState != null) {
                                layoutEmptyState.setVisibility(View.VISIBLE);
                                if (rvGrid != null) rvGrid.setVisibility(View.GONE);
                                tvEmptyTitle.setText("Gagal Memuat Data");
                                tvEmptyDesc.setText(err);
                            }
                        }
                    });
                }
            } catch (Exception e) {
                runOnUiThread(() -> {
                    if (fetchToken != currentFetchToken.get()) return;
                    if (layoutLoadingState != null) layoutLoadingState.setVisibility(View.GONE);
                    if (pbLoading != null) pbLoading.setVisibility(View.GONE);
                    if (swipeRefreshLayout != null) swipeRefreshLayout.setRefreshing(false);
                    if (rvGrid != null) rvGrid.setAlpha(1.0f);
                    showCommandOutput("> tatap$ [ERROR] Gagal terhubung: " + e.getMessage(), true);
                    if (adapter.getItemCount() == 0) {
                        if (layoutPagination != null) layoutPagination.setVisibility(View.GONE);
                        if (layoutEmptyState != null) {
                            layoutEmptyState.setVisibility(View.VISIBLE);
                            if (rvGrid != null) rvGrid.setVisibility(View.GONE);
                            tvEmptyTitle.setText("Koneksi Terputus");
                            tvEmptyDesc.setText(e.getMessage());
                        }
                    }
                });
            }
        }).start();
    }

    private void renderAnimeData(List<JSONObject> list, int count) {
        if (layoutLoadingState != null) layoutLoadingState.setVisibility(View.GONE);
        if (pbLoading != null) pbLoading.setVisibility(View.GONE);
        if (swipeRefreshLayout != null) swipeRefreshLayout.setRefreshing(false);
        if (rvGrid != null) rvGrid.setAlpha(1.0f);
        tvItemCount.setText(count + " judul");
        adapter.setData(list);
        boolean canNext;
        if (hasPagingInfo) {
            canNext = hasNextPage || (totalPages > currentPage);
        } else {
            canNext = count >= 20;
        }
        if (count == 0) {
            canNext = false;
        }

        if (btnNextPage != null) {
            if (btnNextPage.hasFocus() && !canNext) {
                if (btnPrevPage != null && currentPage > 1) {
                    btnPrevPage.requestFocus();
                } else if (rvGrid != null) {
                    rvGrid.requestFocus();
                }
            }
            btnNextPage.setEnabled(canNext);
            btnNextPage.setAlpha(canNext ? 1.0f : 0.4f);
        }
        if (btnPrevPage != null) {
            btnPrevPage.setEnabled(currentPage > 1);
            btnPrevPage.setAlpha(currentPage > 1 ? 1.0f : 0.4f);
        }
        if (tvPageIndicator != null) {
            if (totalPages > 1) {
                tvPageIndicator.setText("Hal " + currentPage + " / " + totalPages);
            } else {
                tvPageIndicator.setText("Hal " + currentPage);
            }
        }

        if (count == 0) {
            if (layoutPagination != null && currentPage == 1) {
                layoutPagination.setVisibility(View.GONE);
            }
            if (layoutEmptyState != null) {
                layoutEmptyState.setVisibility(View.VISIBLE);
                if ("riwayat".equals(currentView)) {
                    tvEmptyTitle.setText("Belum Ada Riwayat Tontonan");
                    tvEmptyDesc.setText("Anime yang Anda tonton akan otomatis tercatat di sini.");
                } else if ("favorit".equals(currentView)) {
                    tvEmptyTitle.setText("Belum Ada Anime Favorit");
                    tvEmptyDesc.setText("Tandai anime favorit Anda dengan menekan tombol + Favorit pada halaman detail.");
                } else if ("jadwal".equals(currentView)) {
                    String dayLabel = getScheduleDayLabel(currentScheduleDay);
                    tvEmptyTitle.setText("Tidak Ada Jadwal Rilis");
                    tvEmptyDesc.setText("Tidak ada rilis anime untuk hari " + dayLabel + " yang tersedia di aplikasi.");
                } else {
                    tvEmptyTitle.setText("Tidak Ada Anime Ditemukan");
                    tvEmptyDesc.setText("Tidak ada judul anime yang cocok dengan filter atau pencarian ini.");
                }
            }
            if (rvGrid != null) rvGrid.setVisibility(View.GONE);
        } else {
            if (layoutPagination != null && !"riwayat".equals(currentView) && !"jadwal".equals(currentView) && !"favorit".equals(currentView)) {
                layoutPagination.setVisibility(View.VISIBLE);
            }
            if (layoutEmptyState != null) layoutEmptyState.setVisibility(View.GONE);
            if (rvGrid != null) {
                rvGrid.setVisibility(View.VISIBLE);
                if (!TvFocusHelper.isTv(MainActivity.this)) {
                    rvGrid.scheduleLayoutAnimation();
                }
                rvGrid.scrollToPosition(0);
                if (TvFocusHelper.isTv(MainActivity.this)) {
                    rvGrid.post(() -> {
                        RecyclerView.ViewHolder vh = rvGrid.findViewHolderForAdapterPosition(0);
                        if (vh != null && vh.itemView != null) {
                            vh.itemView.requestFocus();
                        } else {
                            rvGrid.requestFocus();
                        }
                    });
                }
            }
        }
    }

    private void confirmAndClearHistory() {
        new AlertDialog.Builder(this)
                .setTitle("Hapus Riwayat?")
                .setMessage("Seluruh riwayat anime yang pernah Anda tonton akan dibersihkan.")
                .setPositiveButton("Hapus Semua", (d, w) -> clearWatchHistory())
                .setNegativeButton("Batal", null)
                .show();
    }

    private void clearWatchHistory() {
        showCommandOutput("> tatap$ Menghapus riwayat tontonan...", false);
        new Thread(() -> {
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/history").openConnection();
                conn.setRequestMethod("DELETE");
                conn.setConnectTimeout(3000);
                conn.getResponseCode();
                conn.disconnect();

                getSharedPreferences("tatap_history", Context.MODE_PRIVATE).edit().clear().apply();

                runOnUiThread(() -> {
                    showCommandOutput("> tatap$ [OK] Seluruh riwayat tontonan berhasil dibersihkan", false);
                    if ("riwayat".equals(currentView)) {
                        fetchData();
                    }
                });
            } catch (Exception e) {
                runOnUiThread(() -> showCommandOutput("> tatap$ [ERROR] Gagal hapus riwayat: " + e.getMessage(), true));
            }
        }).start();
    }

    // Model & Adapter for Genre Dialog
    static class GenreItem {
        final String title;
        final String slug;
        GenreItem(String title, String slug) {
            this.title = title;
            this.slug = slug;
        }
    }

    interface OnGenreClickListener {
        void onGenreClick(String slug, String title);
    }

    static class GenreChipAdapter extends RecyclerView.Adapter<GenreChipAdapter.ViewHolder> {
        private final List<GenreItem> allGenres = new ArrayList<>();
        private final List<GenreItem> filteredList = new ArrayList<>();
        private final OnGenreClickListener listener;

        GenreChipAdapter(OnGenreClickListener listener) {
            this.listener = listener;
        }

        void setData(List<GenreItem> data) {
            allGenres.clear();
            filteredList.clear();
            if (data != null) {
                allGenres.addAll(data);
                filteredList.addAll(data);
            }
            notifyDataSetChanged();
        }

        void filter(String query) {
            filteredList.clear();
            if (query == null || query.trim().isEmpty()) {
                filteredList.addAll(allGenres);
            } else {
                String q = query.toLowerCase().trim();
                for (GenreItem item : allGenres) {
                    if (item.title.toLowerCase().contains(q) || item.slug.toLowerCase().contains(q)) {
                        filteredList.add(item);
                    }
                }
            }
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View v = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_genre_chip, parent, false);
            return new ViewHolder(v);
        }

        @Override
        public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
            GenreItem item = filteredList.get(position);
            holder.tvName.setText(item.title);
            holder.itemView.setOnClickListener(v -> {
                if (listener != null) listener.onGenreClick(item.slug, item.title);
            });
        }

        @Override
        public int getItemCount() {
            return filteredList.size();
        }

        static class ViewHolder extends RecyclerView.ViewHolder {
            TextView tvName;
            ViewHolder(@NonNull View itemView) {
                super(itemView);
                tvName = itemView.findViewById(R.id.tv_genre_name);
                TvFocusHelper.attachFocusScale(itemView, 1.08f, 4f);
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

    @Override
    protected void onDestroy() {
        if (tvSidebarAnimator != null) {
            tvSidebarAnimator.cancel();
            tvSidebarAnimator = null;
        }
        super.onDestroy();
    }
}
