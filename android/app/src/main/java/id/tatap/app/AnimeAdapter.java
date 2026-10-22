package id.tatap.app;

import android.content.Context;
import android.content.Intent;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class AnimeAdapter extends RecyclerView.Adapter<RecyclerView.ViewHolder> {
    public static final int VIEW_TYPE_ANIME = 0;
    public static final int VIEW_TYPE_HEADER = 1;

    private final Context context;
    private final List<JSONObject> items = new ArrayList<>();

    public AnimeAdapter(Context context) {
        this.context = context;
    }

    public void setData(List<JSONObject> newItems) {
        items.clear();
        if (newItems != null) {
            items.addAll(newItems);
        }
        notifyDataSetChanged();
    }

    public boolean isHeader(int position) {
        if (position >= 0 && position < items.size()) {
            JSONObject item = items.get(position);
            return item != null && item.optBoolean("is_header", false);
        }
        return false;
    }

    @Override
    public int getItemViewType(int position) {
        return isHeader(position) ? VIEW_TYPE_HEADER : VIEW_TYPE_ANIME;
    }

    @NonNull
    @Override
    public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        if (viewType == VIEW_TYPE_HEADER) {
            View view = LayoutInflater.from(context).inflate(R.layout.item_lane_header, parent, false);
            return new HeaderViewHolder(view);
        } else {
            View view = LayoutInflater.from(context).inflate(R.layout.item_anime_card, parent, false);
            return new AnimeViewHolder(view);
        }
    }

    @Override
    public void onBindViewHolder(@NonNull RecyclerView.ViewHolder rawHolder, int position) {
        JSONObject item = items.get(position);
        if (rawHolder instanceof HeaderViewHolder) {
            HeaderViewHolder holder = (HeaderViewHolder) rawHolder;
            String headerTitle = item.optString("header_title", item.optString("title", "SEKSI ANIME"));
            String lane = item.optString("lane", "");
            holder.tvTitle.setText(headerTitle);

            if ("seasonal".equalsIgnoreCase(lane)) {
                holder.tvSubtitle.setText("[SEASONAL]");
                holder.tvTitle.setTextColor(0xFF38BDF8); // Cyan
                holder.viewIndicator.setBackgroundColor(0xFF38BDF8);
            } else if ("long_running".equalsIgnoreCase(lane)) {
                holder.tvSubtitle.setText("[CONTINUOUS]");
                holder.tvTitle.setTextColor(0xFFF59E0B); // Amber
                holder.viewIndicator.setBackgroundColor(0xFFF59E0B);
            } else {
                holder.tvSubtitle.setText("[LANE]");
                holder.tvTitle.setTextColor(0xFF38BDF8);
                holder.viewIndicator.setBackgroundColor(0xFF38BDF8);
            }
            return;
        }

        AnimeViewHolder holder = (AnimeViewHolder) rawHolder;
        String title = item.optString("title", "Tanpa Judul");
        String poster = item.optString("poster", "");
        String sub = item.optString("sub", "");
        String type = item.optString("type", "");
        String eps = item.optString("eps", "");
        String epsCounter = item.optString("eps_counter", "");
        String slug = item.optString("id", item.optString("slug", ""));
        double score = item.optDouble("score", 0.0);
        String duration = item.optString("duration", "");
        String badge = item.optString("badge", "");
        boolean isFinished = item.optBoolean("is_finished", false);
        boolean isLongRunning = item.optBoolean("is_long_running", false);

        if (!isFinished && !epsCounter.isEmpty()) {
            String[] parts = epsCounter.split("/");
            if (parts.length == 2 && !parts[1].equals("?")) {
                try {
                    int cur = Integer.parseInt(parts[0].trim());
                    int tot = Integer.parseInt(parts[1].trim());
                    if (tot > 0 && cur >= tot) {
                        isFinished = true;
                    }
                } catch (Exception ignored) {}
            }
        }

        holder.tvTitle.setText(title);

        // Format Format/Type Badge (TV, Movie, ONA)
        if (!type.isEmpty()) {
            holder.tvBadgeType.setVisibility(View.VISIBLE);
            holder.tvBadgeType.setText(type.toUpperCase());
        } else {
            holder.tvBadgeType.setVisibility(View.GONE);
        }

        // Format Score Badge (8.5)
        if (score > 0) {
            holder.tvBadgeScore.setVisibility(View.VISIBLE);
            holder.tvBadgeScore.setText(String.format(Locale.US, "%.1f", score));
        } else {
            holder.tvBadgeScore.setVisibility(View.GONE);
        }

        int episode = item.optInt("episode", 0);
        String playedAt = item.optString("played_at", "");

        // Format Subtitle / Status / History Badge (Apple Flat: Nomor Episode Saja)
        if (episode > 0) {
            holder.tvBadgeEp.setText(String.valueOf(episode));
            holder.tvBadgeEp.setBackgroundResource(R.drawable.bg_badge_sub);
            holder.tvBadgeEp.setTextColor(0xFFF1F5F9);
        } else if ("TAMAT".equalsIgnoreCase(badge) || isFinished) {
            holder.tvBadgeEp.setText("TAMAT");
            holder.tvBadgeEp.setBackgroundResource(R.drawable.bg_badge_tamat);
            holder.tvBadgeEp.setTextColor(0xFFECFDF5);
        } else if ("SERIAL PANJANG".equalsIgnoreCase(badge) || isLongRunning) {
            if (!epsCounter.isEmpty()) {
                holder.tvBadgeEp.setText(epsCounter);
            } else if (!eps.isEmpty() && !eps.equals("0")) {
                holder.tvBadgeEp.setText(eps);
            } else if (!sub.isEmpty()) {
                holder.tvBadgeEp.setText(sub);
            } else {
                holder.tvBadgeEp.setText("SERIAL");
            }
            holder.tvBadgeEp.setBackgroundResource(R.drawable.bg_badge_long);
            holder.tvBadgeEp.setTextColor(0xFFFFFBEB);
        } else if (!epsCounter.isEmpty()) {
            holder.tvBadgeEp.setText(epsCounter);
            holder.tvBadgeEp.setBackgroundResource(R.drawable.bg_badge_sub);
            holder.tvBadgeEp.setTextColor(0xFFF1F5F9);
        } else if (!sub.isEmpty()) {
            holder.tvBadgeEp.setText(sub);
            holder.tvBadgeEp.setBackgroundResource(R.drawable.bg_badge_sub);
            holder.tvBadgeEp.setTextColor(0xFFF1F5F9);
        } else if (!eps.isEmpty() && !eps.equals("0")) {
            holder.tvBadgeEp.setText(eps);
            holder.tvBadgeEp.setBackgroundResource(R.drawable.bg_badge_sub);
            holder.tvBadgeEp.setTextColor(0xFFF1F5F9);
        } else {
            holder.tvBadgeEp.setText("ANIME");
            holder.tvBadgeEp.setBackgroundResource(R.drawable.bg_badge_sub);
            holder.tvBadgeEp.setTextColor(0xFFF1F5F9);
        }

        // Format Meta Info
        StringBuilder metaStr = new StringBuilder();
        String scheduleTime = item.optString("time", "");
        if (!playedAt.isEmpty()) {
            metaStr.append("Diputar: ").append(playedAt.length() >= 16 ? playedAt.substring(5, 16) : playedAt);
        } else if (!scheduleTime.isEmpty()) {
            metaStr.append(scheduleTime);
            if (!type.isEmpty()) {
                metaStr.append(" · ").append(type);
            }
        } else {
            if (!epsCounter.isEmpty()) {
                metaStr.append(epsCounter).append(" Ep");
            } else if (!eps.isEmpty() && !eps.equals("0")) {
                metaStr.append(eps).append(" Ep");
            }
            if (!duration.isEmpty()) {
                if (metaStr.length() > 0) metaStr.append(" · ");
                metaStr.append(duration);
            }
            if (metaStr.length() == 0 && !type.isEmpty()) {
                metaStr.append(type);
            }
        }
        holder.tvMeta.setText(metaStr.length() > 0 ? metaStr.toString() : "Tatap Anime");

        ImageLoader.load(poster, holder.ivPoster);

        String synopsis = item.optString("synopsis", "");
        String studio = item.optString("studio", "");
        String season = item.optString("season", "");
        String rawStatus = item.optString("status", isFinished ? "finished" : (badge.equalsIgnoreCase("ONGOING") ? "releasing" : ""));
        final String status = (isFinished && (rawStatus.isEmpty() || rawStatus.equalsIgnoreCase("releasing"))) ? "finished" : rawStatus;
        String source = item.optString("source", "");
        org.json.JSONArray genresArr = item.optJSONArray("genres");
        String genresStr = genresArr != null ? genresArr.toString() : "";

        holder.itemView.setOnClickListener(v -> {
            HapticHelper.performClick(v);
            Intent intent = new Intent(context, DetailActivity.class);
            String itemSlug = slug;
            if (itemSlug == null || itemSlug.isEmpty()) {
                itemSlug = item.optString("id", "");
            }
            String rawMode = item.optString("mode", "sub");
            if (!"dub".equalsIgnoreCase(rawMode)) {
                rawMode = "sub";
            }
            intent.putExtra("slug", itemSlug);
            intent.putExtra("mode", rawMode);
            intent.putExtra("title", title);
            intent.putExtra("poster", poster);
            intent.putExtra("type", type);
            intent.putExtra("eps", eps);
            intent.putExtra("sub", sub);
            intent.putExtra("eps_counter", epsCounter);
            intent.putExtra("synopsis", synopsis);
            intent.putExtra("score", score);
            intent.putExtra("studio", studio);
            intent.putExtra("season", season);
            intent.putExtra("status", status);
            intent.putExtra("source", source);
            intent.putExtra("genres", genresStr);
            context.startActivity(intent);
        });
    }

    @Override
    public int getItemCount() {
        return items.size();
    }

    public static class HeaderViewHolder extends RecyclerView.ViewHolder {
        View viewIndicator;
        TextView tvTitle, tvSubtitle;

        public HeaderViewHolder(@NonNull View itemView) {
            super(itemView);
            viewIndicator = itemView.findViewById(R.id.view_lane_indicator);
            tvTitle = itemView.findViewById(R.id.tv_lane_title);
            tvSubtitle = itemView.findViewById(R.id.tv_lane_subtitle);
            itemView.setFocusable(false);
        }
    }

    public static class AnimeViewHolder extends RecyclerView.ViewHolder {
        ImageView ivPoster;
        TextView tvTitle, tvMeta, tvBadgeEp, tvBadgeScore, tvBadgeType;

        public AnimeViewHolder(@NonNull View itemView) {
            super(itemView);
            ivPoster = itemView.findViewById(R.id.iv_poster);
            tvTitle = itemView.findViewById(R.id.tv_title);
            tvMeta = itemView.findViewById(R.id.tv_meta);
            tvBadgeEp = itemView.findViewById(R.id.tv_badge_ep);
            tvBadgeScore = itemView.findViewById(R.id.tv_badge_score);
            tvBadgeType = itemView.findViewById(R.id.tv_badge_type);

            if (itemView instanceof com.google.android.material.card.MaterialCardView) {
                TvFocusHelper.attachCardFocus((com.google.android.material.card.MaterialCardView) itemView);
            } else {
                TvFocusHelper.attachFocusScale(itemView, 1.06f, 8f);
            }
        }
    }
}
