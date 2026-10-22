package id.tatap.app;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import java.util.Locale;

import androidx.annotation.NonNull;
import androidx.cardview.widget.CardView;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import com.google.android.material.card.MaterialCardView;

public class DetailActivity extends Activity {
    private String slug;
    private String title;
    private String poster;
    private String type;
    private String eps;
    private String sub;
    private String epsCounter;
    private String synopsis;
    private String studio;
    private String season;
    private String status;
    private String source;
    private String genresStr;
    private String mode = "sub";
    private double score = 0.0;

    private TextView tvTitle, tvTitleFull, tvSlug, tvTypeBadge;
    private TextView tvScore, tvStatus, tvInfoLine;
    private View layoutSynopsis, hsvGenres;
    private LinearLayout llGenres;
    private TextView tvSynopsis, btnToggleSynopsis;
    private boolean isSynopsisExpanded = false;
    private ImageView ivPoster;
    private Button btnQuickPlay, btnBookmark, btnSortOrder;
    private boolean isBookmarked = false;
    private ProgressBar pbLoading;
    private RecyclerView rvEpisodes;
    private EpisodeAdapter adapter;

    private SharedPreferences prefs;
    private final List<Integer> originalEpisodes = new ArrayList<>();
    private boolean isAscending = true;

    private View layoutSeasons;
    private RecyclerView rvSeasons;
    private SeasonAdapter seasonAdapter;

    private RecyclerView rvEpisodeRanges;
    private RangeAdapter rangeAdapter;
    private EpisodeRange activeRange = null;

    static class EpisodeRange {
        final int start;
        final int end;
        final String label;
        final boolean isAll;

        EpisodeRange(int start, int end, String label, boolean isAll) {
            this.start = start;
            this.end = end;
            this.label = label;
            this.isAll = isAll;
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_detail);

        slug = getIntent().getStringExtra("slug");
        String passedMode = getIntent().getStringExtra("mode");
        mode = (passedMode != null && !passedMode.isEmpty() && "dub".equalsIgnoreCase(passedMode)) ? "dub" : "sub";
        title = getIntent().getStringExtra("title");
        poster = getIntent().getStringExtra("poster");
        type = getIntent().getStringExtra("type");
        eps = getIntent().getStringExtra("eps");
        sub = getIntent().getStringExtra("sub");
        epsCounter = getIntent().getStringExtra("eps_counter");
        synopsis = getIntent().getStringExtra("synopsis");
        score = getIntent().getDoubleExtra("score", 0.0);
        studio = getIntent().getStringExtra("studio");
        season = getIntent().getStringExtra("season");
        status = getIntent().getStringExtra("status");
        source = getIntent().getStringExtra("source");
        genresStr = getIntent().getStringExtra("genres");

        prefs = getSharedPreferences("tatap_history", Context.MODE_PRIVATE);

        tvTitle = findViewById(R.id.tv_detail_title);
        tvTitleFull = findViewById(R.id.tv_detail_title_full);
        tvSlug = findViewById(R.id.tv_detail_slug);
        tvTypeBadge = findViewById(R.id.tv_detail_type_badge);
        tvScore = findViewById(R.id.tv_detail_score);
        tvStatus = findViewById(R.id.tv_detail_status);
        tvInfoLine = findViewById(R.id.tv_detail_info_line);
        hsvGenres = findViewById(R.id.hsv_detail_genres);
        llGenres = findViewById(R.id.ll_detail_genres);
        layoutSynopsis = findViewById(R.id.layout_detail_synopsis);
        tvSynopsis = findViewById(R.id.tv_detail_synopsis);
        btnToggleSynopsis = findViewById(R.id.btn_toggle_synopsis);
        ivPoster = findViewById(R.id.iv_detail_poster);
        btnQuickPlay = findViewById(R.id.btn_quick_play);
        btnSortOrder = findViewById(R.id.btn_sort_order);
        pbLoading = findViewById(R.id.pb_detail_loading);
        ImageButton btnBack = findViewById(R.id.btn_back);
        rvEpisodes = findViewById(R.id.rv_episodes);
        layoutSeasons = findViewById(R.id.layout_detail_seasons);
        rvSeasons = findViewById(R.id.rv_detail_seasons);
        rvEpisodeRanges = findViewById(R.id.rv_episode_ranges);

        tvTitle.setText(title != null ? title : "Detail Anime");
        tvTitleFull.setText(title != null ? title : "Anime");
        setupSynopsis(synopsis);
        setupMetadata(score, status, studio, season, source, genresStr);

        String badgeText = (type != null && !type.isEmpty() ? type : "ANIME")
                + (epsCounter != null && !epsCounter.isEmpty() ? " · " + epsCounter + " EP" : (eps != null && !eps.isEmpty() ? " · " + eps + " EP" : ""))
                + (sub != null && !sub.isEmpty() ? " · " + sub : "");
        tvTypeBadge.setText(badgeText);
        tvSlug.setText("Memuat episode...");

        if (poster != null && !poster.isEmpty()) {
            ImageLoader.load(poster, ivPoster);
        }

        btnBack.setOnClickListener(v -> {
            HapticHelper.performTick(v);
            finish();
        });
        TvFocusHelper.attachFocusScale(btnBack, 1.1f, 6f);
        TvFocusHelper.attachFocusScale(btnQuickPlay, 1.05f, 6f);
        btnBookmark = findViewById(R.id.btn_detail_bookmark);
        if (btnBookmark != null) {
            TvFocusHelper.attachFocusScale(btnBookmark, 1.05f, 6f);
            btnBookmark.setOnClickListener(v -> {
                HapticHelper.performHeavyClick(v);
                toggleBookmark();
            });
            checkBookmarkStatus();
        }
        TvFocusHelper.attachFocusScale(btnSortOrder, 1.05f, 6f);

        int epSpan = getResources().getInteger(R.integer.episode_grid_columns);
        rvEpisodes.setLayoutManager(new GridLayoutManager(this, epSpan));
        adapter = new EpisodeAdapter();
        rvEpisodes.setAdapter(adapter);
        if (TvFocusHelper.isTv(this)) {
            rvEpisodes.setItemViewCacheSize(8);
        }

        if (rvEpisodeRanges != null) {
            rvEpisodeRanges.setLayoutManager(new androidx.recyclerview.widget.LinearLayoutManager(this, androidx.recyclerview.widget.LinearLayoutManager.HORIZONTAL, false));
            rangeAdapter = new RangeAdapter();
            rvEpisodeRanges.setAdapter(rangeAdapter);
        }

        if (rvSeasons != null) {
            rvSeasons.setLayoutManager(new androidx.recyclerview.widget.LinearLayoutManager(this, androidx.recyclerview.widget.LinearLayoutManager.HORIZONTAL, false));
            seasonAdapter = new SeasonAdapter();
            rvSeasons.setAdapter(seasonAdapter);
        }

        btnSortOrder.setOnClickListener(v -> {
            HapticHelper.performTick(v);
            isAscending = !isAscending;
            btnSortOrder.setText(isAscending ? "1 - N" : "N - 1");
            updateEpisodeDisplay();
        });

        btnQuickPlay.setOnClickListener(v -> {
            HapticHelper.performClick(v);
            int targetEp = prefs.getInt("last_ep_" + slug, -1);
            if (targetEp <= 0) {
                if (!originalEpisodes.isEmpty()) {
                    targetEp = originalEpisodes.get(0);
                } else {
                    targetEp = 1;
                }
            }
            playEpisode(targetEp);
        });

        updateQuickPlayButton();
        if (TvFocusHelper.isTv(this)) {
            btnQuickPlay.post(() -> btnQuickPlay.requestFocus());
        }
        loadEpisodes();
        loadRelations();
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateQuickPlayButton();
        if (adapter != null) {
            adapter.notifyDataSetChanged();
        }
    }

    private void updateQuickPlayButton() {
        int lastEp = prefs.getInt("last_ep_" + slug, -1);
        if (btnQuickPlay instanceof com.google.android.material.button.MaterialButton) {
            com.google.android.material.button.MaterialButton mb = (com.google.android.material.button.MaterialButton) btnQuickPlay;
            mb.setAllCaps(false);
            mb.setIconResource(R.drawable.ic_play);
            if (lastEp > 0) {
                mb.setText("Lanjutkan " + lastEp);
                mb.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFF0A84FF));
                mb.setTextColor(0xFFFFFFFF);
                mb.setIconTint(android.content.res.ColorStateList.valueOf(0xFFFFFFFF));
                mb.setStrokeColor(android.content.res.ColorStateList.valueOf(0xFF0A84FF));
                mb.setStrokeWidth((int) (1 * getResources().getDisplayMetrics().density));
            } else {
                mb.setText("Putar 1");
                mb.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFF0A84FF));
                mb.setTextColor(0xFFFFFFFF);
                mb.setIconTint(android.content.res.ColorStateList.valueOf(0xFFFFFFFF));
                mb.setStrokeColor(android.content.res.ColorStateList.valueOf(0xFF0A84FF));
                mb.setStrokeWidth((int) (1 * getResources().getDisplayMetrics().density));
            }
        } else {
            if (lastEp > 0) {
                btnQuickPlay.setText("Lanjutkan " + lastEp);
            } else {
                btnQuickPlay.setText("Putar 1");
            }
        }
    }

    private void playEpisode(int ep) {
        prefs.edit()
                .putInt("last_ep_" + slug, ep)
                .putBoolean("watched_" + slug + "_" + ep, true)
                .apply();

        // Rekam riwayat tontonan ke backend lokal
        new Thread(() -> {
            try {
                JSONObject b = new JSONObject();
                b.put("slug", slug);
                b.put("title", title != null ? title : slug);
                b.put("episode", ep);
                b.put("poster", poster != null ? poster : "");
                b.put("type", type != null ? type : "");
                b.put("mode", "sub");

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

        Intent intent = new Intent(DetailActivity.this, PlayerActivity.class);
        intent.putExtra("slug", slug);
        intent.putExtra("ep", ep);
        intent.putExtra("mode", mode != null ? mode : "sub");
        intent.putExtra("title", title);
        intent.putExtra("poster", poster);
        intent.putExtra("type", type);
        intent.putIntegerArrayListExtra("episode_list", new ArrayList<>(originalEpisodes));
        startActivity(intent);
    }

    private void loadEpisodes() {
        if (pbLoading != null) pbLoading.setVisibility(View.VISIBLE);
        new Thread(() -> {
            try {
                String u = "http://127.0.0.1:8767/api/anime/" + URLEncoder.encode(slug, "UTF-8") + "/episodes";
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(10000);
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                reader.close();

                JSONObject res = new JSONObject(sb.toString());
                if (res.optBoolean("success")) {
                    JSONObject dataObj = res.getJSONObject("data");
                    JSONArray epsArr = dataObj.getJSONArray("episodes");
                    String apiSynopsis = dataObj.optString("synopsis", "");
                    List<Integer> list = new ArrayList<>();
                    for (int i = 0; i < epsArr.length(); i++) {
                        list.add(epsArr.getJSONObject(i).getInt("ep"));
                    }
                    Collections.sort(list);
                    JSONObject detailObj = dataObj.optJSONObject("detail");
                    if (detailObj != null) {
                        double apiScore = detailObj.optDouble("score", 0.0);
                        String apiStatus = detailObj.optString("status", "");
                        String apiStudio = detailObj.optString("studio", "");
                        String apiSeason = detailObj.optString("season", "");
                        String apiSource = detailObj.optString("source", "");
                        JSONArray apiGenres = detailObj.optJSONArray("genres");
                        String apiGenresStr = apiGenres != null ? apiGenres.toString() : "";
                        runOnUiThread(() -> {
                            if (score <= 0 && apiScore > 0) score = apiScore;
                            String sLowerApi = apiStatus.toLowerCase();
                            boolean apiFinished = sLowerApi.contains("finish") || sLowerApi.contains("tamat") || sLowerApi.contains("completed");
                            if (apiFinished || (status == null || status.isEmpty())) {
                                if (!apiStatus.isEmpty()) status = apiStatus;
                            }
                            if ((studio == null || studio.isEmpty()) && !apiStudio.isEmpty()) studio = apiStudio;
                            if ((season == null || season.isEmpty()) && !apiSeason.isEmpty()) season = apiSeason;
                            if ((source == null || source.isEmpty()) && !apiSource.isEmpty()) source = apiSource;
                            if ((genresStr == null || genresStr.isEmpty()) && !apiGenresStr.isEmpty()) genresStr = apiGenresStr;
                            setupMetadata(score, status, studio, season, source, genresStr);
                        });
                    }

                    runOnUiThread(() -> {
                        if (pbLoading != null) pbLoading.setVisibility(View.GONE);
                        originalEpisodes.clear();
                        originalEpisodes.addAll(list);
                        if ((synopsis == null || synopsis.trim().isEmpty() || apiSynopsis.length() > synopsis.length()) && !apiSynopsis.trim().isEmpty()) {
                            synopsis = apiSynopsis;
                            setupSynopsis(apiSynopsis);
                        }

                        boolean isFinishedAnime = false;
                        if (status != null && !status.isEmpty()) {
                            String sLower = status.toLowerCase();
                            if (sLower.contains("finish") || sLower.contains("tamat") || sLower.contains("completed")) {
                                isFinishedAnime = true;
                            }
                        }
                        if (epsCounter != null && !epsCounter.isEmpty()) {
                            String[] parts = epsCounter.split("/");
                            if (parts.length == 2 && !parts[1].equals("?")) {
                                try {
                                    int cur = Integer.parseInt(parts[0].trim());
                                    int tot = Integer.parseInt(parts[1].trim());
                                    if (tot > 0 && cur >= tot) {
                                        isFinishedAnime = true;
                                    }
                                } catch (Exception ignored) {}
                            }
                        }
                        if (!isFinishedAnime && !list.isEmpty() && epsCounter != null && !epsCounter.isEmpty()) {
                            String[] parts = epsCounter.split("/");
                            if (parts.length == 2 && !parts[1].equals("?")) {
                                try {
                                    int tot = Integer.parseInt(parts[1].trim());
                                    if (tot > 0 && list.size() >= tot) {
                                        isFinishedAnime = true;
                                    }
                                } catch (Exception ignored) {}
                            }
                        }

                        if (isFinishedAnime) {
                            if (status == null || !status.toLowerCase().contains("finish")) {
                                status = "finished";
                                setupMetadata(score, status, studio, season, source, genresStr);
                            }
                        }

                        String countStr;
                        if (epsCounter != null && !epsCounter.isEmpty()) {
                            String[] parts = epsCounter.split("/");
                            if (parts.length == 2 && !parts[1].equals("?")) {
                                if (isFinishedAnime) {
                                    countStr = list.size() + "/" + parts[1] + " Episode (Tamat)";
                                } else {
                                    countStr = list.size() + "/" + parts[1] + " Episode Rilis (Sedang Tayang)";
                                }
                            } else {
                                if (isFinishedAnime) {
                                    countStr = list.size() + " Episode (Tamat)";
                                } else {
                                    countStr = list.size() + " Episode Rilis (Sedang Tayang)";
                                }
                            }
                        } else {
                            if (isFinishedAnime) {
                                countStr = list.size() + " Episode (Tamat)";
                            } else {
                                countStr = list.size() + " Episode Tersedia";
                            }
                        }
                        tvSlug.setText(countStr);
                        setupEpisodeRanges(list);
                        updateEpisodeDisplay();
                        updateQuickPlayButton();
                    });
                } else {
                    runOnUiThread(() -> {
                        if (pbLoading != null) pbLoading.setVisibility(View.GONE);
                        tvSlug.setText("Episode tidak ditemukan");
                    });
                }
            } catch (Exception e) {
                runOnUiThread(() -> {
                    if (pbLoading != null) pbLoading.setVisibility(View.GONE);
                    Toast.makeText(this, "Gagal memuat episode: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                    tvSlug.setText("Gagal terhubung ke backend");
                });
            }
        }).start();
    }

    private void setupMetadata(double scoreVal, String statusVal, String studioVal, String seasonVal, String sourceVal, String genresData) {
        // Score Badge
        if (tvScore != null) {
            if (scoreVal > 0) {
                tvScore.setText(String.format(Locale.US, "%.1f", scoreVal));
                tvScore.setVisibility(View.VISIBLE);
            } else {
                tvScore.setVisibility(View.GONE);
            }
        }

        // Status Badge
        if (tvStatus != null) {
            if (statusVal != null && !statusVal.trim().isEmpty()) {
                String sLower = statusVal.trim().toLowerCase();
                if (sLower.contains("finish") || sLower.contains("tamat") || sLower.contains("completed")) {
                    tvStatus.setText("TAMAT");
                    tvStatus.setBackgroundResource(R.drawable.bg_detail_status_finished);
                    tvStatus.setTextColor(0xFF10B981);
                    tvStatus.setVisibility(View.VISIBLE);
                } else if (sLower.contains("releas") || sLower.contains("airing") || sLower.contains("ongoing")) {
                    tvStatus.setText("ONGOING");
                    tvStatus.setBackgroundResource(R.drawable.bg_detail_status_ongoing);
                    tvStatus.setTextColor(0xFF38BDF8);
                    tvStatus.setVisibility(View.VISIBLE);
                } else {
                    tvStatus.setVisibility(View.GONE);
                }
            } else {
                tvStatus.setVisibility(View.GONE);
            }
        }

        // Info Line
        if (tvInfoLine != null) {
            List<String> metaParts = new ArrayList<>();
            if (studioVal != null && !studioVal.trim().isEmpty()) {
                metaParts.add("Studio: " + studioVal.trim());
            }
            if (seasonVal != null && !seasonVal.trim().isEmpty()) {
                metaParts.add(seasonVal.trim());
            }
            if (sourceVal != null && !sourceVal.trim().isEmpty()) {
                metaParts.add("Sumber: " + sourceVal.trim());
            }
            if (!metaParts.isEmpty()) {
                tvInfoLine.setText(android.text.TextUtils.join(" · ", metaParts));
                tvInfoLine.setVisibility(View.VISIBLE);
            } else {
                tvInfoLine.setVisibility(View.GONE);
            }
        }

        // Genre Chips
        if (llGenres != null && hsvGenres != null) {
            if (genresData != null && !genresData.trim().isEmpty()) {
                try {
                    List<String> genreList = new ArrayList<>();
                    if (genresData.startsWith("[")) {
                        JSONArray jArr = new JSONArray(genresData);
                        for (int i = 0; i < jArr.length(); i++) {
                            String g = jArr.optString(i, "").trim();
                            if (!g.isEmpty() && !"hentai".equalsIgnoreCase(g)) {
                                genreList.add(g);
                            }
                        }
                    } else {
                        for (String g : genresData.split(",")) {
                            String trimmed = g.trim();
                            if (!trimmed.isEmpty() && !"hentai".equalsIgnoreCase(trimmed)) {
                                genreList.add(trimmed);
                            }
                        }
                    }

                    if (!genreList.isEmpty()) {
                        llGenres.removeAllViews();
                        for (String genreName : genreList) {
                            TextView chip = new TextView(this);
                            chip.setText(genreName);
                            chip.setTextColor(0xFFCBD5E1);
                            chip.setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP, 10.5f);
                            chip.setBackgroundResource(R.drawable.bg_detail_genre_chip);
                            int padH = (int) (8 * getResources().getDisplayMetrics().density);
                            int padV = (int) (4 * getResources().getDisplayMetrics().density);
                            chip.setPadding(padH, padV, padH, padV);
                            chip.setFocusable(true);
                            chip.setClickable(true);
                            TvFocusHelper.attachFocusScale(chip, 1.08f, 4f);
                            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                                    LinearLayout.LayoutParams.WRAP_CONTENT,
                                    LinearLayout.LayoutParams.WRAP_CONTENT);
                            lp.setMarginEnd((int) (6 * getResources().getDisplayMetrics().density));
                            chip.setLayoutParams(lp);
                            chip.setOnClickListener(v -> {
                                HapticHelper.performClick(v);
                                Intent intent = new Intent(DetailActivity.this, MainActivity.class);
                                intent.putExtra("genre", genreName);
                                intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                                startActivity(intent);
                                finish();
                            });
                            llGenres.addView(chip);
                        }
                        hsvGenres.setVisibility(View.VISIBLE);
                    } else {
                        hsvGenres.setVisibility(View.GONE);
                    }
                } catch (Exception ignored) {
                    hsvGenres.setVisibility(View.GONE);
                }
            } else {
                hsvGenres.setVisibility(View.GONE);
            }
        }
    }

    private void setupSynopsis(String synopsisText) {
        if (layoutSynopsis == null || tvSynopsis == null || btnToggleSynopsis == null) {
            if (layoutSynopsis != null) layoutSynopsis.setVisibility(View.GONE);
            return;
        }

        if (synopsisText == null || synopsisText.trim().isEmpty()) {
            layoutSynopsis.setVisibility(View.GONE);
            return;
        }

        layoutSynopsis.setVisibility(View.VISIBLE);
        tvSynopsis.setText(synopsisText.trim());
        isSynopsisExpanded = false;
        final int defaultLines = TvFocusHelper.isTv(this) ? 3 : 2;
        tvSynopsis.setMaxLines(defaultLines);
        btnToggleSynopsis.setText("Selengkapnya ▼");

        if (TvFocusHelper.isTv(this)) {
            TvFocusHelper.attachFocusScale(btnToggleSynopsis, 1.05f, 4f);
        }

        View.OnClickListener toggleListener = v -> {
            HapticHelper.performClick(v);
            isSynopsisExpanded = !isSynopsisExpanded;
            if (isSynopsisExpanded) {
                tvSynopsis.setMaxLines(Integer.MAX_VALUE);
                btnToggleSynopsis.setText("Lipat ke Judul ▲");
            } else {
                tvSynopsis.setMaxLines(defaultLines);
                btnToggleSynopsis.setText("Selengkapnya ▼");
            }
        };

        btnToggleSynopsis.setOnClickListener(toggleListener);
        tvSynopsis.setOnClickListener(toggleListener);
    }

    private void setupEpisodeRanges(List<Integer> list) {
        if (rvEpisodeRanges == null) return;
        if (list != null && list.size() > 100) {
            rvEpisodeRanges.setVisibility(View.VISIBLE);
            List<EpisodeRange> ranges = new ArrayList<>();
            int total = list.size();
            int step = 100;
            for (int s = 1; s <= total; s += step) {
                int e = Math.min(s + step - 1, total);
                ranges.add(new EpisodeRange(s, e, s + " - " + e, false));
            }
            ranges.add(new EpisodeRange(1, total, "Semua (" + total + ")", true));

            int lastPlayedEp = prefs.getInt("last_ep_" + slug, -1);
            activeRange = ranges.get(0);
            if (lastPlayedEp > 0) {
                for (int i = 0; i < ranges.size() - 1; i++) {
                    EpisodeRange r = ranges.get(i);
                    if (lastPlayedEp >= r.start && lastPlayedEp <= r.end) {
                        activeRange = r;
                        break;
                    }
                }
            }
            if (rangeAdapter != null) {
                rangeAdapter.setRanges(ranges, activeRange);
            }
        } else {
            rvEpisodeRanges.setVisibility(View.GONE);
            activeRange = null;
        }
    }

    private void updateEpisodeDisplay() {
        List<Integer> displayList = new ArrayList<>();
        if (activeRange != null && !activeRange.isAll) {
            for (int ep : originalEpisodes) {
                if (ep >= activeRange.start && ep <= activeRange.end) {
                    displayList.add(ep);
                }
            }
        } else {
            displayList.addAll(originalEpisodes);
        }
        if (!isAscending) {
            Collections.reverse(displayList);
        }
        adapter.setEpisodes(displayList);
    }

    class EpisodeAdapter extends RecyclerView.Adapter<EpisodeAdapter.EpisodeViewHolder> {
        private final List<Integer> episodes = new ArrayList<>();
        private int cachedLastPlayedEp = -1;
        private final Set<Integer> cachedWatchedSet = new HashSet<>();

        public void setEpisodes(List<Integer> list) {
            episodes.clear();
            cachedWatchedSet.clear();
            cachedLastPlayedEp = prefs.getInt("last_ep_" + slug, -1);
            if (list != null) {
                episodes.addAll(list);
                for (int ep : list) {
                    if (prefs.getBoolean("watched_" + slug + "_" + ep, false)) {
                        cachedWatchedSet.add(ep);
                    }
                }
            }
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public EpisodeViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_episode, parent, false);
            return new EpisodeViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull EpisodeViewHolder holder, int position) {
            int ep = episodes.get(position);
            holder.tvTitle.setText(String.valueOf(ep));

            if (ep == cachedLastPlayedEp) {
                // Last played episode: Apple System Blue (Nomor Saja)
                holder.card.setCardBackgroundColor(0xFF162A45);
                holder.card.setStrokeColor(0xFF0A84FF);
                holder.tvTitle.setTextColor(0xFF0A84FF);
                holder.tvTitle.setTypeface(null, android.graphics.Typeface.BOLD);
                holder.tvBadge.setVisibility(View.GONE);
            } else if (cachedWatchedSet.contains(ep)) {
                // Watched episode: Apple Muted Surface (Nomor Saja)
                holder.card.setCardBackgroundColor(0xFF141418);
                holder.card.setStrokeColor(0xFF222228);
                holder.tvTitle.setTextColor(0xFF71717A);
                holder.tvTitle.setTypeface(null, android.graphics.Typeface.NORMAL);
                holder.tvBadge.setVisibility(View.GONE);
            } else {
                // Unwatched episode: Apple Clean Elevated Surface (Nomor Saja)
                holder.card.setCardBackgroundColor(0xFF1C1C22);
                holder.card.setStrokeColor(0xFF2C2E38);
                holder.tvTitle.setTextColor(0xFFF5F5F7);
                holder.tvTitle.setTypeface(null, android.graphics.Typeface.NORMAL);
                holder.tvBadge.setVisibility(View.GONE);
            }

            holder.itemView.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                playEpisode(ep);
            });
        }

        @Override
        public int getItemCount() {
            return episodes.size();
        }

        class EpisodeViewHolder extends RecyclerView.ViewHolder {
            MaterialCardView card;
            TextView tvTitle;
            TextView tvBadge;

            public EpisodeViewHolder(@NonNull View itemView) {
                super(itemView);
                card = itemView.findViewById(R.id.card_episode);
                tvTitle = itemView.findViewById(R.id.tv_ep_title);
                tvBadge = itemView.findViewById(R.id.tv_ep_status_badge);
                TvFocusHelper.attachFocusScale(itemView, 1.08f, 6f);
            }
        }
    }

    class RangeAdapter extends RecyclerView.Adapter<RangeAdapter.RangeViewHolder> {
        private final List<EpisodeRange> ranges = new ArrayList<>();
        private EpisodeRange selectedRange;

        public void setRanges(List<EpisodeRange> list, EpisodeRange selected) {
            ranges.clear();
            if (list != null) ranges.addAll(list);
            this.selectedRange = selected;
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public RangeViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_range_chip, parent, false);
            return new RangeViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull RangeViewHolder holder, int position) {
            EpisodeRange r = ranges.get(position);
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
                activeRange = r;
                notifyDataSetChanged();
                updateEpisodeDisplay();
            });
        }

        @Override
        public int getItemCount() {
            return ranges.size();
        }

        class RangeViewHolder extends RecyclerView.ViewHolder {
            MaterialCardView card;
            TextView tvLabel;

            public RangeViewHolder(@NonNull View itemView) {
                super(itemView);
                card = itemView.findViewById(R.id.card_range_chip);
                tvLabel = itemView.findViewById(R.id.tv_range_label);
                TvFocusHelper.attachFocusScale(itemView, 1.08f, 6f);
            }
        }
    }

    private void loadRelations() {
        if (slug == null || slug.isEmpty()) return;
        new Thread(() -> {
            try {
                String u = "http://127.0.0.1:8767/api/anime/" + URLEncoder.encode(slug, "UTF-8") + "/relations"
                        + "?title=" + URLEncoder.encode(title != null ? title : "", "UTF-8");
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(12000);
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                reader.close();

                JSONObject res = new JSONObject(sb.toString());
                if (res.optBoolean("success")) {
                    JSONArray relArr = res.getJSONObject("data").getJSONArray("relations");
                    List<JSONObject> list = new ArrayList<>();
                    for (int i = 0; i < relArr.length(); i++) {
                        JSONObject item = relArr.getJSONObject(i);
                        String itemSlug = item.optString("slug", "");
                        if (!itemSlug.isEmpty() && !itemSlug.equals(slug)) {
                            list.add(item);
                        }
                    }
                    runOnUiThread(() -> {
                        if (!list.isEmpty() && seasonAdapter != null && layoutSeasons != null) {
                            seasonAdapter.setRelations(list);
                            layoutSeasons.setVisibility(View.VISIBLE);
                        } else if (layoutSeasons != null) {
                            layoutSeasons.setVisibility(View.GONE);
                        }
                    });
                }
            } catch (Exception ignored) {
                runOnUiThread(() -> {
                    if (layoutSeasons != null) layoutSeasons.setVisibility(View.GONE);
                });
            }
        }).start();
    }

    class SeasonAdapter extends RecyclerView.Adapter<SeasonAdapter.SeasonViewHolder> {
        private final List<JSONObject> relations = new ArrayList<>();

        public void setRelations(List<JSONObject> list) {
            relations.clear();
            if (list != null) relations.addAll(list);
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public SeasonViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_season_chip, parent, false);
            return new SeasonViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull SeasonViewHolder holder, int position) {
            JSONObject item = relations.get(position);
            String relType = item.optString("relation", "");
            String label = item.optString("label", "Season");
            String relTitle = item.optString("title", "");
            String relSlug = item.optString("slug", "");
            String relPoster = item.optString("poster", "");
            String relFormat = item.optString("format", "TV");

            holder.tvBadge.setText(label.toUpperCase());
            holder.tvTitle.setText(relTitle);

            if ("PREQUEL".equalsIgnoreCase(relType)) {
                holder.tvBadge.setTextColor(0xFF38BDF8); // Cyan
            } else if ("SEQUEL".equalsIgnoreCase(relType)) {
                holder.tvBadge.setTextColor(0xFFC084FC); // Purple
            } else if ("MOVIE".equalsIgnoreCase(relFormat)) {
                holder.tvBadge.setTextColor(0xFFFACC15); // Gold/Yellow
            } else if ("OVA".equalsIgnoreCase(relFormat) || "SPECIAL".equalsIgnoreCase(relFormat) || "ONA".equalsIgnoreCase(relFormat)) {
                holder.tvBadge.setTextColor(0xFF34D399); // Emerald / Mint
            } else {
                holder.tvBadge.setTextColor(0xFF94A3B8); // Slate
            }

            holder.itemView.setOnClickListener(v -> {
                HapticHelper.performClick(v);
                Intent intent = new Intent(DetailActivity.this, DetailActivity.class);
                intent.putExtra("slug", relSlug);
                intent.putExtra("title", relTitle);
                intent.putExtra("poster", relPoster.isEmpty() ? poster : relPoster);
                intent.putExtra("type", relFormat);
                intent.putExtra("eps", "");
                intent.putExtra("sub", "SUB");
                startActivity(intent);
                finish();
            });
        }

        @Override
        public int getItemCount() {
            return relations.size();
        }

        class SeasonViewHolder extends RecyclerView.ViewHolder {
            TextView tvBadge;
            TextView tvTitle;

            public SeasonViewHolder(@NonNull View itemView) {
                super(itemView);
                tvBadge = itemView.findViewById(R.id.tv_season_badge);
                tvTitle = itemView.findViewById(R.id.tv_season_title);
                TvFocusHelper.attachFocusScale(itemView, 1.08f, 6f);
            }
        }
    }

    private void checkBookmarkStatus() {
        if (slug == null || slug.isEmpty()) return;
        new Thread(() -> {
            try {
                URL u = new URL("http://127.0.0.1:8767/api/bookmarks/check?slug=" + URLEncoder.encode(slug, "UTF-8"));
                HttpURLConnection conn = (HttpURLConnection) u.openConnection();
                conn.setConnectTimeout(3000);
                conn.setReadTimeout(3000);
                if (conn.getResponseCode() == 200) {
                    BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) sb.append(line);
                    reader.close();
                    JSONObject obj = new JSONObject(sb.toString());
                    if (obj.optBoolean("success", false)) {
                        JSONObject data = obj.optJSONObject("data");
                        boolean b = data != null && data.optBoolean("bookmarked", false);
                        runOnUiThread(() -> updateBookmarkUI(b));
                    }
                }
            } catch (Exception ignored) {}
        }).start();
    }

    private void updateBookmarkUI(boolean bookmarked) {
        this.isBookmarked = bookmarked;
        if (btnBookmark == null) return;
        if (bookmarked) {
            btnBookmark.setText("Tersimpan");
            btnBookmark.setTextColor(0xFFFBBF24);
            btnBookmark.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFF2A2210));
            if (btnBookmark instanceof com.google.android.material.button.MaterialButton) {
                com.google.android.material.button.MaterialButton mb = (com.google.android.material.button.MaterialButton) btnBookmark;
                mb.setAllCaps(false);
                mb.setIconResource(R.drawable.ic_star_filled);
                mb.setIconTint(android.content.res.ColorStateList.valueOf(0xFFFBBF24));
            }
        } else {
            btnBookmark.setText("+ Favorit");
            btnBookmark.setTextColor(0xFF94A3B8);
            btnBookmark.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFF1E2433));
            if (btnBookmark instanceof com.google.android.material.button.MaterialButton) {
                com.google.android.material.button.MaterialButton mb = (com.google.android.material.button.MaterialButton) btnBookmark;
                mb.setAllCaps(false);
                mb.setIconResource(R.drawable.ic_star_outline);
                mb.setIconTint(android.content.res.ColorStateList.valueOf(0xFF94A3B8));
            }
        }
    }

    private void toggleBookmark() {
        if (slug == null || slug.isEmpty()) return;
        boolean nextState = !isBookmarked;
        updateBookmarkUI(nextState);
        Toast.makeText(this, nextState ? "Tersimpan ke Favorit" : "Dihapus dari Favorit", Toast.LENGTH_SHORT).show();

        new Thread(() -> {
            try {
                if (nextState) {
                    URL u = new URL("http://127.0.0.1:8767/api/bookmarks");
                    HttpURLConnection conn = (HttpURLConnection) u.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setDoOutput(true);
                    conn.setConnectTimeout(3000);
                    conn.setReadTimeout(3000);
                    JSONObject body = new JSONObject();
                    body.put("slug", slug);
                    body.put("title", title != null ? title : "");
                    body.put("poster", poster != null ? poster : "");
                    body.put("type", type != null ? type : "");
                    body.put("sub", sub != null ? sub : "");
                    body.put("eps", eps != null ? eps : "");
                    body.put("score", 0.0);
                    java.io.OutputStream out = conn.getOutputStream();
                    out.write(body.toString().getBytes("UTF-8"));
                    out.flush();
                    out.close();
                    conn.getResponseCode();
                } else {
                    URL u = new URL("http://127.0.0.1:8767/api/bookmarks/" + URLEncoder.encode(slug, "UTF-8"));
                    HttpURLConnection conn = (HttpURLConnection) u.openConnection();
                    conn.setRequestMethod("DELETE");
                    conn.setConnectTimeout(3000);
                    conn.setReadTimeout(3000);
                    conn.getResponseCode();
                }
            } catch (Exception e) {
                runOnUiThread(() -> checkBookmarkStatus());
            }
        }).start();
    }
}
