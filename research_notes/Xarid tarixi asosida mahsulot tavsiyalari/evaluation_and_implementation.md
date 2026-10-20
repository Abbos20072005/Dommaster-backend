# Evaluation and practical implementation of purchase-history recommendations (Django + PostgreSQL + Redis, cron batch, no ML infrastructure) — state of practice as of October 2026

Reading notes for the report writer:

- "Cited Findings" contain only what was read in a source during this research session. Several sources were reached only through search-result summaries (marked "via search summary") — treat those as weaker.
- "Inferences" contain my own engineering reasoning, SQL and code sketches. **All SQL / Python in Inferences is written by me, untested, and not taken from a source.** Table names such as `service_order` / `service_orderitem` are Django-default guesses for this project and must be checked against the models.
- "Project context" refers to the repository's `CLAUDE.md` (Dommaster backend), not to a web source.
- Sources that could not be opened (HTTP 403): the Netflix interleaving blog post and the Dentons article on the 2026 Uzbek amendment. Claims that depend on them are flagged.

---

## 1. Offline evaluation: metrics, data splitting, sampled metrics, offline-online gap, minimal protocol and mandatory baselines

### Takeaway
Offline evaluation is a cheap screening step, not a verdict: the literature repeatedly shows that the offline winner often does not win online, that sampled metrics and non-temporal splits can flip model rankings, and that well-tuned simple baselines (popularity, item-kNN) beat most "advanced" models. For a small shop the sensible protocol is a global temporal split, full (unsampled) ranking over the catalog, and always reporting against popularity and category-popularity baselines.

### Cited Findings
- Krichene & Rendle (KDD 2020, best-paper award) show that sampled metrics (ranking the held-out item against a small random subset of items instead of the full catalog) are inconsistent with the exact metrics: they do not preserve "A is better than B" statements, even in expectation. — [Google Research publication page](https://research.google/pubs/on-sampled-metrics-for-item-recommendation/); [IJCAI 2021 extended abstract](https://www.ijcai.org/proceedings/2021/651)
- The smaller the sample, the less the metrics differ from each other; at very small sample sizes all metrics collapse to AUC. The authors advise against sampling during evaluation and, if sampling is unavoidable, propose corrections (minimising bias or MSE). — [IJCAI 2021 extended abstract](https://www.ijcai.org/proceedings/2021/651); related preprint by Rendle, "Evaluation Metrics for Item Recommendation under Sampling": [arXiv 1912.02263](https://arxiv.org/abs/1912.02263)
- The KDD 2020 award for this paper is confirmed by a community news post. — [recommender-systems.com](https://recommender-systems.com/news/2020/09/16/50-of-the-best-paper-awards-at-kdd-2020-go-to-recommender-systems-papers/)
- Ji, Sun, Zhang & Li (ACM TOIS 41(3), 2023; arXiv preprint 2020 under the title "On Offline Evaluation of Recommender Systems") define data leakage as not observing the global timeline when splitting train/test: the model learns from interactions that would not be available at prediction time. With the popular leave-last-one-out split, BPR, NeuMF, SASRec and LightGCN on MovieLens-25M, Yelp, Amazon-music and Amazon-electronic all recommended "future" items, and the relative order of the models became unpredictable depending on how much future data leaked. They propose a timeline evaluation scheme. — [arXiv 2010.11060](https://arxiv.org/abs/2010.11060v4) (via search summary of the abstract)
- Cañamares, Castells & Moffat (Information Retrieval Journal, 2020, "Offline evaluation options for recommender systems") find that changing the train/test split, the metric, how target items are selected, or how empty recommendation lists are handled can produce different or even opposite comparison outcomes. — [catalog record](https://katalog.hcu-hamburg.de/vufind/Search2Record/SPR040124959) (via search summary)
- Castells & Moffat (AI Magazine, 2022, open access) position offline evaluation as a complement to online experiments, note that the methodology was inherited from ML and IR whose assumptions recommendation violates, and list experimental biases and the cyclic (feedback) nature of recommendation as open challenges. — [AI Magazine article page](https://ojs.aaai.org/index.php/aimagazine/article/view/21745) (abstract only, via search summary)
- Ferrari Dacrema, Cremonesi & Jannach (RecSys 2019, best full paper) examined 18 neural top-n recommendation papers from KDD, SIGIR, WWW and RecSys (2015–2018): only 7 were reproducible with reasonable effort; 6 of those 7 were often outperformed by simple, properly tuned methods, and the 7th did not consistently beat a tuned linear model (SLIM). — [ar5iv 1907.06902](https://ar5iv.labs.arxiv.org/html/1907.06902)
- The simple baselines in that study: TopPopular (non-personalised most-popular), ItemKNN and UserKNN (cosine with shrinkage), content and hybrid ItemKNN variants, and the graph random-walk methods P3alpha and RP3beta (the latter divides similarity by item popularity to a power beta). Baselines were tuned with Bayesian search, 35 configurations each. — [ar5iv 1907.06902](https://ar5iv.labs.arxiv.org/html/1907.06902)
- Methodology errors found in the reproduced papers: choosing the number of epochs on the test set, untuned baselines, a non-standard NDCG implementation, and a published test split that was much more popularity-skewed than a random split (Gini 0.92 versus about 0.79). — [ar5iv 1907.06902](https://ar5iv.labs.arxiv.org/html/1907.06902)
- Jannach & Jugovac (ACM TMIS 2019 research commentary) report Netflix's statement that offline results were not as predictive of A/B outcomes as hoped, and list studies where the most accurate offline model did not win online or in perceived quality: Rossetti et al. 2016, Cremonesi et al. 2012, Garcin et al. 2014, Maksai et al. 2015, Beel & Langer 2015, Jannach & Lerche 2017, Ekstrand et al. 2014, McNee et al. 2002. Counter-examples where offline did predict online: Brovman et al. 2016, Cremonesi et al. 2013, Kamehkhosh & Jannach 2017. — [ar5iv 1908.08328](https://ar5iv.labs.arxiv.org/html/1908.08328)
- The same review notes that higher offline recall can simply reflect a tendency to recommend popular items (Jannach et al. 2015), that recommenders may mostly suggest items customers would have bought anyway (Bodapati 2008), and that Netflix itself blends a substantial amount of unpersonalised popularity into ranking. — [ar5iv 1908.08328](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Booking.com (Bernardi, Mavridis & Estevez, KDD 2019, about 150 customer-facing models): one of the six lessons is that model performance is not the same as business performance; the authors recommend validating business impact with randomised controlled trials. — [Adrian Colyer's summary of the paper](https://blog.acolyer.org/2019/10/07/150-successful-machine-learning-models/) (via search summary; the paper itself was not opened)
- Explanations attributed to the Booking.com paper for the weak offline-to-business link: value saturation, segment saturation (new and old model increasingly agree, so few users see a difference), and over-optimising a proxy metric. — [Daily Dose of Data Science write-up](https://www.dailydoseofds.com/llmops-mlops-miscellaneous-part-1/) (secondary source, not verified against the paper)
- Amazon's Prime Video team used a temporal protocol: sort the data chronologically, cut at a time point, and check whether at least one of six recommendations was watched in the two weeks after the cutoff. Their first autoencoder lost to both item-to-item collaborative filtering and a plain bestseller list; only after retraining on time-ordered data did it win. — [Amazon Science, history of Amazon's recommendation algorithm](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Amazon's stated default when nothing is known about a user is to recommend the most popular items. — [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Google's "Rules of ML" recommends measuring the delta between an old and a new model on the same sample before launching (Rule #24) and separating training-vs-holdout, holdout-vs-next-day and next-day-vs-live gaps (Rule #37). — [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)

### Inferences
- Standard metric definitions (textbook knowledge, not fetched from a source in this session), with K = the number of slots the widget really shows:
  - Precision@K = relevant items in top K / K. Recall@K = relevant items in top K / all relevant items of that test case. HitRate@K = share of test cases with at least one relevant item in top K (with exactly one held-out item, HitRate@K equals Recall@K).
  - MRR = mean of 1 / rank of the first relevant item. MAP = mean over test cases of average precision. NDCG@K = DCG@K / ideal DCG@K with gain discounted by log2(rank + 1).
  - Catalog coverage@K = distinct products that appear in anyone's top K / active products. Diversity = e.g. average number of distinct item categories (or 1 − average pairwise similarity) inside a list. Novelty / popularity bias = average popularity rank (or mean −log2 of popularity share) of recommended items, or Gini of recommendation exposure.
- A minimal offline protocol that fits tens of thousands of products and modest order volume:
  1. **Global temporal split.** Train on all non-cancelled orders before date T; test on orders in [T, T + 4–8 weeks]; keep one more earlier window for tuning. Never tune on the test window (the error Dacrema et al. found in published code).
  2. **Never split order lines randomly.** A random split puts part of a basket in train and the rest in test, which makes co-purchase models look far better than they are (this is the leakage Ji et al. describe, in its worst form for basket data).
  3. **Two test tasks matching the two widget types.** (a) Basket completion for "bought together": for each test order with ≥ 2 products, hide one product, use the others as seeds, rank. (b) Next purchase for personal blocks: use the customer's history before T as seeds, relevant = any product bought in the test window (Amazon's "at least one of six within two weeks" is exactly HitRate@6).
  4. **Full ranking, no sampled negatives.** With 10^4–10^5 products, scoring the entire active catalog per test case is trivial, so the Krichene & Rendle problem is avoided entirely. Candidates = products that existed and were active at T.
  5. **Baselines that must always be in the table:** global popularity (time-decayed), popularity inside the seed product's item category / sub category, "customer's own previously bought products" (a very strong baseline wherever consumables are re-ordered), and random. A model that does not beat category popularity is not worth shipping.
  6. **Report beyond accuracy:** HitRate@K / Recall@K / NDCG@K plus coverage@K, average popularity of recommended items, and category diversity. Report by seed-support segment (products with ≥ 20 orders, 5–19, < 5) because most of the catalog is cold.
  7. **Uncertainty:** with a few thousand test orders, bootstrap confidence intervals over orders/customers; differences inside the interval are noise.
- Project-specific data hygiene: exclude cancelled orders (`ORDER_STATUS` 4, project context), treat one order as one basket of distinct products, cap or drop very large baskets (contractor/B2B orders), and decide deliberately whether "prorab" customers are evaluated separately — their baskets look different from retail ones.
- Expect the offline number to mainly measure "can the model reproduce what people bought without recommendations". It cannot measure whether a recommendation caused an additional purchase; only an online test or holdout can.

### Gaps
- The full texts of Castells & Moffat (2022) and Cañamares et al. (2020) were not opened; only abstract-level claims are cited. Their specific recommendations on split configuration are not captured.
- The Booking.com KDD 2019 paper was not read directly; the three "why" explanations come from a secondary blog.
- I found no published study that evaluates recommenders specifically on building-materials / DIY retail data.
- No source was fetched that gives the formal metric definitions; they are given from background knowledge.

---

## 2. Online evaluation: A/B metrics, attribution, sample size, low-traffic alternatives, guardrails

### Takeaway
Widget CTR is the easiest metric to move and the least trustworthy; field evidence shows CTR and revenue can diverge and that widget position and size alone can double CTR. With modest traffic, a classic A/B test on revenue is usually under-powered, so the realistic toolkit is: high-frequency primary metrics (widget add-to-cart), long-running persistent holdouts for incrementality, interleaving for ranker-versus-ranker comparisons, and before/after comparisons only with explicit seasonality caveats.

### Cited Findings
- Business measures used in published field tests of recommenders fall into five groups: click-through rate, adoption/conversion, sales and revenue, effects on the sales distribution, and user engagement. — [Jannach & Jugovac, ar5iv 1908.08328](https://ar5iv.labs.arxiv.org/html/1908.08328)
- CTR and revenue can diverge: at eBay one test (Brovman et al. 2016) showed only about 3% CTR gain but about 6% revenue gain, whereas other eBay tests reported +36–38% CTR. — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Direct versus indirect effect in grocery retail: Dias et al. 2008 measured about 0.3% direct revenue from recommendations but up to 26% indirect revenue in one category; Lawrence et al. 2001 measured 1.8% direct revenue. — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- A purchase-based collaborative filter produced a 35% sales lift on DVDs in a field experiment, while the view-based variant had no significant effect (Lee & Hosanagar 2014). — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Pitfalls documented in the review: CTR can be inflated by clickbait-like items; improved recommendations "stole" clicks from other page areas at Google News (Liu et al. 2010); non-purchase proxies (views, demo downloads) did not predict business success in mobile games; many tests ran only days or weeks and miss long-term effects; statistics and sample sizes were often missing; a change of widget position and size alone raised CTR by 100% (Garcin et al. 2014). — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Before/after and removal comparisons appear in the literature with acknowledged confounds: a video-on-demand study estimated a 15.5% sales lift from a before/after comparison (Bambini et al. 2011); an online bookstore saw revenue fall 17% when the recommender was switched off for a month, with seasonality named as a possible confound (Shani et al. 2005). — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Recommended practice from the same review: align the success metric with business strategy, validate that proxies such as CTR correlate with the real objective, test UI and placement together with algorithms, run longer tests with planned sample sizes, and track sales distribution/diversity as well as volume. — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Kohavi, Tang & Xu's book distinguishes organisational guardrail metrics (protect the business) from trust-related guardrails, and treats Sample Ratio Mismatch (SRM) as the key trust guardrail. — [Cambridge University Press chapter page](https://www.cambridge.org/core/books/trustworthy-online-controlled-experiments/sample-ratio-mismatch-and-other-trustrelated-guardrail-metrics/8DBB0F59AC7729D7BC6B94690DB9CCD5) (via search summary)
- SRM (observed split differs from the designed split) is a symptom of data-quality problems; a taxonomy and rules of thumb are given by Fabijan et al., KDD 2019. — [paper page](https://www.lukasvermeer.nl/publications/papers/2019/07/25/diagnosing-sample-ratio-mismatch-in-online-controlled-experiments.html) (via search summary)
- A common SRM check is a chi-square goodness-of-fit test with a strict threshold such as p < 0.001. — [MetricGate docs](https://metricgate.com/docs/sample-ratio-mismatch-test/) (vendor documentation, via search summary)
- Kohavi et al.'s "Seven Rules of Thumb for Web Site Experimenters" (KDD 2014) includes "have enough users"; the experiments behind the paper involved at least hundreds of thousands of users, most of them millions. — [Colyer's summary](https://blog.acolyer.org/2017/09/26/seven-rules-of-thumb-for-web-site-experimenters/); [paper page](https://exp-platform.com/rules-of-thumb/) (via search summary)
- Evan Miller's sample-size calculator takes baseline conversion rate, minimum detectable effect (absolute or relative), statistical power and significance level as inputs. — [Evan Miller, sample size calculator](https://www.evanmiller.org/ab-testing/sample-size.html)
- Interleaving: Netflix described (2017, Aurisset, Ramm & Parks) a two-stage process — a fast interleaving stage prunes many candidate ranking algorithms, then a traditional A/B test runs on the survivors. — [Data Science Weekly excerpt](https://www.datascienceweekly.org/newsletter/data-science-weekly-newsletter-issue-211); [ClickZ](https://www.clickz.com/machine-learning-choice-paralysis-netflix-personalizes-title-images/) (both via search summary; the original Netflix post returned HTTP 403)
- Interleaving shows each user one list merged from both rankers (team-draft: the two algorithms alternately pick items, and the system records which one contributed each item), so each user is their own control; published research is summarised as needing 10 to 100 times fewer users than an A/B test for the same effect. — [Spotify Confidence glossary](https://confidence.spotify.com/glossary/interleaving) (via search summary)
- Google's Rules of ML, Rule #2: instrument metrics before building the system and build an experiment framework that buckets users. — [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)

### Inferences
- Metric set for a recommendation widget (my proposal):
  - **Widget level (diagnostic):** impression-to-click rate, impression-to-add-to-cart rate, share of widget loads that returned fewer than N items / used a fallback.
  - **Attributed (direct):** orders and revenue containing a product that the customer clicked or added from a widget within the attribution window.
  - **Session/visitor level (decision metrics):** conversion, revenue per visitor, average order value, items (distinct products) per order.
  - **Incremental:** revenue per visitor of exposed group minus holdout group — the only number that answers "did recommendations add sales" (see Bodapati's "would have bought anyway" problem above).
  - **Guardrails:** overall conversion and revenue per visitor must not drop; API latency (p95) and error rate of the pages hosting the widget; cancellation/refund rate of orders containing recommended items; SRM check on bucket sizes; share of recommended items that are out of stock.
- Sample size reality check. Using the common rule of thumb n per arm ≈ 16·p(1−p)/δ² for a two-sided test at 5% significance and 80% power (I recall this from Kohavi et al.'s book but **could not verify the exact formula in a source this session**; it matches standard power calculations):
  - Order conversion 3%, detect +5% relative (δ = 0.0015): about 207,000 visitors per arm.
  - Order conversion 2%, detect +10% relative (δ = 0.002): about 78,000 visitors per arm.
  - Widget click rate 5%, detect +20% relative (δ = 0.01): about 7,600 widget viewers per arm.
  Conclusion: a mid-size store can realistically A/B-test widget-level rates, rarely order-level revenue. Revenue per visitor has much higher variance than a binary conversion, so it needs even more.
- What to do when traffic is too low for revenue A/B tests:
  1. **Persistent global holdout.** Assign 5–10% of customers/cookie tokens (stable hash of the id) to "no personalised recommendations" (they see popularity or nothing) for months. Small per-day sample, but it accumulates and measures total incremental value.
  2. **Choose a sensitive primary metric** (add-to-cart from widget) for algorithm-versus-algorithm decisions and treat revenue only as a guardrail.
  3. **Interleaving** when comparing two rankers for the same slot: one list, each item tagged with its source algorithm, credit by clicks/add-to-carts. It measures preference between rankers only, not long-term or revenue effects.
  4. **Before/after** only as supporting evidence: compare whole weeks, same weekday mix, and add a difference-in-differences control (categories or a platform where the widget was not launched). Building materials are strongly seasonal, so naive before/after is especially risky; the bookstore example above shows the confound.
  5. **Bandits** (epsilon-greedy / Thompson sampling over a handful of widget variants) reduce the cost of showing a bad variant but are an allocation method, not a clean measurement; keep a fixed-share control anyway. (No source was fetched on bandits — background knowledge.)
- Test hygiene: randomise by customer id when logged in, otherwise by the cookie token; keep assignment sticky across app and site where the user is identifiable; run whole weeks (at least two); decide the metric and duration before starting; do not stop at the first "significant" day.
- Attribution windows: I found no authoritative standard. A defensible approach is to store raw events and compute several windows in SQL afterwards (same session; 24 hours after click; 7 days after click) and to report "direct" (clicked item bought) separately from "assisted" (order placed after any widget click). Because building-materials purchases are often planned over days, the 7-day number should be reported alongside the 24-hour one.

### Gaps
- The original Netflix interleaving post could not be opened (403), so the exact claimed efficiency figure and the reported correlation between interleaving and A/B metrics are unverified; the "10–100x" range comes from a vendor glossary.
- The 16σ²/δ² rule and "run at least one to two full weeks" guidance were not verified against Kohavi et al.'s book in this session.
- Evan Miller's page is a JavaScript calculator; no reliable numeric example could be extracted from it.
- No authoritative source was found for recommendation attribution-window conventions or for typical recommendation-widget CTR / revenue-share benchmarks in DIY retail.
- No sourced material on bandits for low-traffic recommendation widgets was collected.

---

## 3. What to log from day one; recommended event schema

### Takeaway
Without impression logs carrying algorithm version, placement and position, neither online evaluation nor later model training is possible, and position/size effects alone can swamp algorithm effects. The de-facto industry schema (GA4 e-commerce: `view_item_list` → `select_item` → `add_to_cart` → `purchase`, with `item_list_id`, `item_list_name` and `index` on every item) maps directly onto a small first-party events table.

### Cited Findings
- GA4's e-commerce schema defines list events `view_item_list` and `select_item` with event-level `item_list_id` and `item_list_name` and an `items` array; each item carries `item_id`, `index`, `item_list_id`, `item_list_name`, `price`, `quantity`. — [Google Analytics 4 e-commerce developer guide](https://developers.google.com/analytics/devguides/collection/ga4/ecommerce)
- In the GA4 examples, the `add_to_cart` and `purchase` items keep the same `item_list_id` / `item_list_name` (the example list is "related_products") and `index`, which is how a purchase is tied back to the list where the product was found. `purchase` adds `transaction_id`, `value`, `currency`. — [GA4 e-commerce guide](https://developers.google.com/analytics/devguides/collection/ga4/ecommerce)
- The GA4 page does not spell out an attribution rule; carrying the list fields forward is the client's responsibility. The `items` array is limited to 200 elements. — [GA4 e-commerce guide](https://developers.google.com/analytics/devguides/collection/ga4/ecommerce)
- Rules of ML: track as much as possible in the current system before formalising the ML system (Rule #2); log the features used at serving time so they can be reused for training (Rule #29). — [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- A widget position and size change alone doubled CTR in one field study, and recommendation gains partly came at the expense of clicks elsewhere on the page — so placement and position must be recorded with each impression. — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Project context: `OrderItem` stores no price, the order channel (site/app) is not stored, and customer language is not stored. — repository `CLAUDE.md` (project instructions)

### Inferences
- Minimal first-party schema (one PostgreSQL table, append-only; my design):

  | Field | Purpose |
  |---|---|
  | `id` (bigserial), `created_at` | ordering, partitioning by month |
  | `event_type` | `impression`, `click`, `add_to_cart`, `purchase` |
  | `rec_request_id` (UUID) | generated by the API for every recommendation response; returned to the client; echoed back on click / add-to-cart; the join key for everything |
  | `customer_id` (nullable), `anon_token` | logged-in customer or the cookie token (`cart_token` in this project) |
  | `platform` | site / ios / android (the project does not store channel on orders, so this is the only place it will exist) |
  | `placement` | e.g. `pdp_bought_together`, `pdp_similar`, `cart_cross_sell`, `home_for_you`, `order_success` |
  | `algorithm`, `algo_version` | e.g. `copurchase_cosine`, `2026-10-09` (date or run id of the nightly build) |
  | `experiment`, `variant` | A/B bucket or `holdout` |
  | `seed_product_ids` (int array) | what the list was computed from |
  | `product_id`, `position`, `score`, `fallback_level` | the item shown, its rank, its score, and which level of the fallback chain produced it |
  | `price_at_event`, `quantity`, `order_id` | filled for add-to-cart / purchase; price snapshot is required because `OrderItem` keeps no price |

- Impression logging options: (a) server-side "served" log — one row per response with an array of product ids (cheap, complete, but counts lists that were never scrolled into view); (b) client-side "viewed" event sent when the widget becomes visible. Start with (a) on day one; add (b) later. Label the metric accordingly ("served CTR" versus "viewed CTR").
- Attribution plumbing: the client sends `rec_request_id` and `position` with the add-to-cart call; store them on the cart item and copy them to the order item at checkout (or write a `purchase` event at order creation by joining cart-item attribution). This avoids fuzzy time-window joins and survives multi-day carts.
- Always log the control/holdout group's "would-have-been-shown" request too (with `variant = holdout`), otherwise exposed-versus-holdout comparisons are biased toward users who reached pages with widgets.
- Volume: even at 50,000 widget responses per day with array-style impression rows, this is about 1.5 million rows per month — comfortably within plain PostgreSQL. Partition by month or delete raw impressions older than N months after aggregating daily counts.
- Purchases that came through a recommendation click should be flagged so they can later be excluded or discounted when computing popularity and co-purchase (feedback-loop control, see section 9).

### Gaps
- The GA4 events reference (exact parameter types/requirements) was not opened; types above are inferred from the guide's examples.
- No public description of a small shop's first-party recommendation event table was found; the schema above is my own synthesis.

---

## 4. Item-item co-purchase in plain SQL on PostgreSQL

### Takeaway
A self-join of the order-items table on `order_id` yields pair counts from which support, confidence, lift, cosine and Jaccard are one arithmetic expression each; at 100k–1M order lines a nightly full rebuild into a "top-N per product" table is simpler and safer than incremental maintenance or a materialised view. The two real hazards are very large baskets (quadratic pair explosion) and rare-pair noise (lift is unstable at low counts), and raw co-counts are dominated by bestsellers.

### Cited Findings
- The standard SQL pattern joins `order_items a` to `order_items b` on equal `order_id` with `a.product_id < b.product_id` (each unordered pair once), counts distinct orders per pair, filters by a minimum pair count in `HAVING`, and computes item support as the share of orders containing the item. — [OneUptime, market basket analysis in ClickHouse (March 2026)](https://oneuptime.com/blog/post/2026-03-31-clickhouse-market-basket-analysis/view) (ClickHouse syntax; via search summary — no PostgreSQL-specific tutorial with concrete SQL was found)
- Apache MADlib ships an in-database association-rules (Apriori) module for PostgreSQL that reports support, confidence, lift, leverage and conviction; lift of 1 means the two items are independent. — [MADlib assoc_rules source on PGXN](https://api.pgxn.org/src/madlib/madlib-1.14.0/src/ports/postgres/modules/assoc_rules/assoc_rules.sql_in) (via search summary; version 1.14 is old)
- Amazon found that raw co-purchase counts make bestsellers the top recommendation for every product; their relatedness instead compares the observed co-purchase rate with what would be expected by chance (B is related to A if buyers of A buy B more than the average customer does). — [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Amazon later corrected for heavy buyers: customers who bought A tend to buy more of everything, so the expected count was underestimated; discounting heavy buyers' contribution gave a large quality improvement. — [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Amazon rebuilt the related-items list for every product offline once a day, which was feasible with early-2000s hardware; item-level computation is cheap because few customers buy any given product. — [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- PostgreSQL's `REFRESH MATERIALIZED VIEW` completely replaces the view's contents by re-running the query; without `CONCURRENTLY` it can block readers; `CONCURRENTLY` requires a plain-column `UNIQUE` index covering all rows, a populated view, and only one refresh may run at a time; the non-concurrent refresh tends to be faster when many rows change. The documentation describes no incremental refresh. Current documentation is PostgreSQL 18 (18.6); PostgreSQL 19 was in beta in September 2026. — [PostgreSQL docs, REFRESH MATERIALIZED VIEW](https://www.postgresql.org/docs/current/sql-refreshmaterializedview.html)

### Inferences
- **All SQL below is mine, untested, with assumed table names (`service_order`, `service_orderitem`) and the project's status code 4 = cancelled.**

  Step 1 — baskets of distinct products, cancelled orders removed, giant and single-item baskets dropped:

  ```sql
  CREATE TEMP TABLE basket AS
  SELECT DISTINCT oi.order_id, oi.product_id
  FROM service_orderitem oi
  JOIN service_order o ON o.id = oi.order_id
  WHERE o.status <> 4
    AND o.created_at >= now() - interval '24 months';

  DELETE FROM basket b
  USING (SELECT order_id FROM basket
         GROUP BY order_id
         HAVING count(*) < 2 OR count(*) > 50) x
  WHERE b.order_id = x.order_id;

  CREATE INDEX ON basket (order_id, product_id);
  ANALYZE basket;
  ```

  Step 2 — pair counts and all five measures, keep top 30 per product:

  ```sql
  WITH n AS (SELECT count(DISTINCT order_id)::float8 AS n FROM basket),
  item AS (SELECT product_id, count(*) AS cnt FROM basket GROUP BY 1),
  pair AS (
    SELECT a.product_id AS a, b.product_id AS b, count(*) AS cab
    FROM basket a
    JOIN basket b ON b.order_id = a.order_id AND b.product_id <> a.product_id
    GROUP BY 1, 2
    HAVING count(*) >= 3                      -- minimum co-purchase count
  ),
  scored AS (
    SELECT p.a, p.b, p.cab,
           p.cab / n.n                                   AS support,
           p.cab::float8 / ia.cnt                        AS confidence,   -- P(b | a)
           p.cab * n.n / (ia.cnt::float8 * ib.cnt)       AS lift,
           p.cab / sqrt(ia.cnt::float8 * ib.cnt)         AS cosine,
           p.cab::float8 / (ia.cnt + ib.cnt - p.cab)     AS jaccard
    FROM pair p
    JOIN item ia ON ia.product_id = p.a
    JOIN item ib ON ib.product_id = p.b
    CROSS JOIN n
  )
  SELECT * FROM (
    SELECT s.*, row_number() OVER (PARTITION BY a ORDER BY cosine DESC, cab DESC) AS rn
    FROM scored s
  ) r
  WHERE rn <= 30;
  ```

  `count(*)` is safe because `basket` already holds distinct (order, product) rows. Using `<>` produces both directions, which is what a per-product top-N needs; using `<` halves the join and the result can be mirrored with `UNION ALL`.
- Which score to rank by: confidence favours bestsellers (the Amazon problem); lift favours rare coincidences (a pair bought together twice out of two purchases gets a huge lift); cosine and Jaccard sit in between. Practical choice: rank by cosine (or lift with a shrinkage term, e.g. `cab / (sqrt(ca * cb) + lambda)`), require a minimum `cab`, and store all measures so the ranking can be changed without recomputing. Pick the variant by offline evaluation (section 1).
- Why basket-size capping matters: a basket with n distinct products generates n·(n−1) ordered pairs. An order with 200 lines produces 39,800 pair rows — as many as roughly 3,300 four-item orders — and such orders (contractor bulk purchases) connect unrelated products. Cap at something like 30–50 distinct products, or down-weight each pair by 1/(n−1) (a simple analogue of Amazon's heavy-buyer correction).
- Sparse data variant: if most orders contain one product, also compute "same customer within N days" co-occurrence by joining on `customer_id` with a date-window condition instead of `order_id`, and store it as a separate relation type.
- Run time (reasoned estimate, **not measured and not sourced**): the work is proportional to the sum of n² over baskets, not to the number of order lines. With about 1M order lines in about 250k orders averaging 4 products and capped baskets, the join yields on the order of a few million pair rows before aggregation — the kind of hash join / aggregate PostgreSQL finishes in seconds to a few minutes on a small server with adequate `work_mem`. Verify with `EXPLAIN (ANALYZE, BUFFERS)` on real data; uncapped baskets are what turn it into hours.
- Full rebuild versus incremental: incremental pair-count upserts (`INSERT ... ON CONFLICT DO UPDATE SET cnt = cnt + 1`) must also handle cancellations, the rolling time window and item-count changes, and every score depends on global counts anyway. At this scale a nightly full rebuild is simpler and self-healing.
- Materialised view versus table: a materialised view gives no incremental benefit (full recompute per the docs), cannot carry `algo_version`, and is awkward to manage in Django migrations. A regular table managed by a model, filled by a management command inside one transaction (`DELETE` old relation type + `INSERT ... SELECT`), or filled under a new `run_id` and then switched by updating a single "current run" pointer, gives atomic swaps and history. Because this bypasses the ORM, no Django signals fire (project context: bulk operations skip signals) — clear any related cache keys by hand or version them (section 5).
- Cron: `manage.py build_product_relations` nightly, following the project's existing pattern of cron-run commands such as `recalculate_badges` (project context). Guard against overlapping runs with `pg_try_advisory_lock`.

### Gaps
- No PostgreSQL-specific engineering blog post with concrete co-occurrence SQL and timings was found; the cited pattern is from a ClickHouse guide and the PostgreSQL SQL above is my adaptation.
- No published benchmark of this self-join at 100k–1M order lines on PostgreSQL was found; the run-time statement is an estimate.
- Amazon's exact heavy-buyer correction formula is in the 2017 IEEE Internet Computing paper "Two Decades of Recommender Systems at Amazon.com", which was not retrieved.
- MADlib's compatibility with PostgreSQL 17/18 was not checked.

---

## 5. Storing and serving: precomputed table vs Redis, per-customer lists, cache keys/TTL, latency

### Takeaway
The proven pattern is Amazon's: an offline-built "product → related products" table plus a cheap online merge of those lists for the customer's recent items; batch is good enough before considering anything real-time. For this stack PostgreSQL should be the source of truth for the relation table and Redis only a cache of finished lists — sorted sets are optional and only worth it if merging is done inside Redis.

### Cited Findings
- Amazon's serving design: offline, a related-items list per product (refreshed daily); online, for each item the visitor recently bought, fetch its list, merge the candidates and weight each by how related it is to the visitor's purchases; items recurring across lists rise. User-to-user matching was rejected as too slow at request time. — [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Alibaba follows the same shape at larger scale: item nearest neighbours are computed offline and loaded into an item-to-item key-value store; online, the user's recent items retrieve candidates from it. — [Eugene Yan, System Design for Recommendations and Search](https://eugeneyan.com/writing/system-design-for-discovery/)
- Eugene Yan's advice: split the system into offline (build artifacts) and online (serve under latency constraints) and into retrieval and ranking; build retrieval first and add a ranker later; question whether real-time is needed before building it, because batch recommendations may be good enough. Post-processing online includes filtering and business logic. — [Eugene Yan](https://eugeneyan.com/writing/system-design-for-discovery/)
- Redis sorted sets use the compact listpack encoding while a set has at most 128 entries and members of at most 64 bytes (defaults of `zset-max-listpack-entries` / `-value`); above that they convert to skiplist + hash table. — [OneUptime, zset-max-listpack-entries (March 2026)](https://oneuptime.com/blog/post/2026-03-31-redis-configure-zset-max-listpack-entries/view) (blog, via search summary)
- Blog-level memory estimates: roughly 28–36 bytes per (score, member) pair in listpack versus roughly 100–136 bytes in skiplist encoding, plus per-key overhead; these should be verified with `MEMORY USAGE` on real data. — [OneUptime, estimating memory for sorted sets](https://oneuptime.com/blog/post/2026-03-31-redis-estimate-memory-for-sorted-sets-workload/markdown) (blog, via search summary; figures differ between posts)
- `ZREVRANGE` is the legacy form; since Redis 6.2 `ZRANGE ... REV` is preferred. — [OneUptime, ZRANGE / ZREVRANGE](https://oneuptime.com/blog/post/2026-03-31-redis-zrange-zrevrange-sorted-set/view) (blog, via search summary)
- Project context: Redis is the Django cache backend at a fixed local address; the code base caches with manual keys and TTLs of 600–86,400 s; the published home layout is cached 5 minutes per platform and language; product lists must go through `get_optimized_product_qs` to get cart/favourite annotations without N+1 queries. — repository `CLAUDE.md`

### Inferences
- Relation table (my design), e.g. `ProductRelation`: `product_id`, `related_product_id`, `relation_type` (`bought_together`, `similar`, `same_customer`, ...), `score`, `rank`, `support` (co-purchase count), `algo_version`, `computed_at`; unique on (`product_id`, `relation_type`, `related_product_id`); index on (`product_id`, `relation_type`, `rank`). 50,000 products × 30 neighbours × 2 types = 3M narrow rows — small for PostgreSQL, and a single-product lookup is one index range scan.
- PostgreSQL table versus Redis sorted sets:
  - Table: survives restarts and cache flushes, joins to `Product` for stock/active filters, is inspectable in the admin panel, and holds version history. This should be the system of record.
  - Redis: use it as a cache of the *final ordered id list* per key through the existing Django cache API (a JSON/pickled list is enough). Sorted sets (one key per product, top 30 stays in listpack) only pay off if the per-customer merge is done in Redis with `ZUNIONSTORE`; with a local PostgreSQL and a 3M-row table, a single SQL aggregate does the same merge without adding a second data model.
- Per-customer lists — compute on request, not nightly:

  ```sql
  -- seeds: last purchases / cart / recently viewed, with weights (recency, source)
  SELECT r.related_product_id, sum(r.score * s.weight) AS score
  FROM service_productrelation r
  JOIN unnest(%(seed_ids)s::int[], %(weights)s::float8[]) AS s(product_id, weight)
       ON s.product_id = r.product_id
  WHERE r.relation_type = 'bought_together'
    AND r.related_product_id <> ALL(%(seed_ids)s)
  GROUP BY 1
  ORDER BY score DESC
  LIMIT 100;
  ```

  Reasons: most customers do not visit on a given day, so nightly per-customer precomputation wastes work and is stale the moment the customer adds something to the cart; the on-request merge is one indexed query over at most (seeds × 30) rows. Nightly per-customer materialisation is only justified for outbound channels (push/e-mail campaigns) where there is no request.
- Cache keys and TTLs (proposal consistent with project conventions):
  - `rec:{algo_version}:rel:{type}:{product_id}` → raw candidate ids + scores, TTL 24 h. Putting `algo_version` (the nightly run id) in the key makes the nightly switch atomic and removes the need for explicit invalidation.
  - `rec:{algo_version}:cust:{customer_id or anon_token}:{placement}` → merged candidate ids, TTL 10–30 min; delete on order creation and (optionally) on cart change.
  - Cache *candidates*, not the final response: stock, `is_active`, cart contents and price change faster than relations, so filtering and serialisation happen after the cache read on every request.
  - Fallback lists (bestsellers per item category, global) under their own keys, TTL 1–24 h.
- Latency: serve widgets from a separate endpoint that the app/site calls after the main screen loads, so a slow or failing recommender never blocks the product page; give the endpoint a hard server-side time budget and return the fallback list when exceeded. A warm path is one cache read plus one product query; a cold path adds one indexed relation query. I found no authoritative published latency budget for mobile recommendation APIs, so any numeric target (for example p95 under 200 ms server-side) is a team decision, not a cited standard.

### Gaps
- Eugene Yan's article gives no latency figures; no authoritative mobile-API latency budget for recommendation widgets was found.
- Redis memory numbers are from blog posts that disagree slightly; official Redis memory-optimisation docs were not opened.
- No public write-up comparing "Postgres table + cache" with "Redis sorted sets" for a shop of this size was found.

---

## 6. pgvector in practice for a Django project

### Takeaway
pgvector (v0.8.7 in the README at research time, PostgreSQL 13+) has first-class Django support through the `pgvector` Python package (`VectorExtension`, `VectorField`, `HnswIndex`, `IvfflatIndex`, distance functions). It is not needed for co-purchase recommendations; at 10k–100k products it is only worth adding for content-based "similar products" / cold-start from embeddings, and even then exact (index-free) search in a nightly batch is sufficient.

### Cited Findings
- pgvector's README installs tag v0.8.7, supports PostgreSQL 13+, and is available as APT package `postgresql-18-pgvector` (replace 18 with the server version), Yum/DNF `pgvector_18`, Homebrew, PGXN, conda-forge and Docker image `pgvector/pgvector:pg18-trixie` (tags for PostgreSQL 13–18). — [pgvector README](https://github.com/pgvector/pgvector)
- Windows installation requires building with Visual Studio C++ tools: set `PGROOT`, then `nmake /F Makefile.win` and `nmake /F Makefile.win install` from an x64 Native Tools prompt run as administrator. — [pgvector README](https://github.com/pgvector/pgvector)
- Limits: `vector` can be indexed up to 2,000 dimensions (stored up to 16,000); `halfvec` indexed up to 4,000; `bit` up to 64,000; `sparsevec` up to 1,000 non-zero elements with HNSW only. — [pgvector README](https://github.com/pgvector/pgvector)
- HNSW defaults: `m = 16`, `ef_construction = 64`, `hnsw.ef_search = 40`. IVFFlat guidance: lists = rows/1000 up to 1M rows (sqrt(rows) above), probes start at sqrt(lists), and the index should be created after the table has data. — [pgvector README](https://github.com/pgvector/pgvector)
- Without an index pgvector does exact nearest-neighbour search with perfect recall; approximate indexes trade recall for speed, and for a small table a sequential scan may be faster than an index. — [pgvector README](https://github.com/pgvector/pgvector)
- Filtering caveat: with approximate indexes the `WHERE` filter is applied after the index scan, so with default `ef_search = 40` and a filter matching 10% of rows only about 4 rows come back on average; iterative index scans (`hnsw.iterative_scan`, since 0.8.0; `hnsw.max_scan_tuples` default 20,000), partial indexes or partitioning address this. — [pgvector README](https://github.com/pgvector/pgvector)
- HNSW builds are much faster when the graph fits in `maintenance_work_mem`; in Docker, `--shm-size` must be at least that value for parallel builds. — [pgvector README](https://github.com/pgvector/pgvector)
- Django integration in pgvector-python: enable the extension with a migration containing `VectorExtension()` from `pgvector.django`; fields `VectorField(dimensions=...)`, `HalfVectorField`, `BitField`, `SparseVectorField`; query by ordering on `L2Distance`, `CosineDistance`, `MaxInnerProduct`, `L1Distance`, `HammingDistance` or `JaccardDistance`; distances can be annotated and filtered (`distance__lt`); `Avg` and `Sum` aggregates work on vectors. — [pgvector-python README](https://github.com/pgvector/pgvector-python)
- Index classes go in `Meta.indexes`: `HnswIndex(name, fields, m, ef_construction, opclasses)` and `IvfflatIndex(name, fields, lists, opclasses)` with opclasses `vector_l2_ops`, `vector_ip_ops`, `vector_cosine_ops`; half-precision expression indexes use `OpClass(Cast(...))` and need `django.contrib.postgres` in `INSTALLED_APPS`. — [pgvector-python README](https://github.com/pgvector/pgvector-python)
- Package version: the PyPI package name is `pgvector`; one mirror lists 0.4.2 (released 5 December 2025, Python ≥ 3.9) as latest while piwheels lists a 0.5.0 dated 6 July 2026 — the sources conflict. — [CERN simple-repository mirror](https://simple-repository.app.cern.ch/project/pgvector); [piwheels](https://www.piwheels.org/project/pgvector/) (both via search summary)

### Inferences
- Minimal Django usage (my sketch using the documented API names, untested):

  ```python
  # migration
  from pgvector.django import VectorExtension
  operations = [VectorExtension()]

  # model
  from pgvector.django import VectorField, HnswIndex, CosineDistance

  class ProductEmbedding(BaseModel):
      product = models.OneToOneField("service.Product", on_delete=models.CASCADE)
      embedding = VectorField(dimensions=384)

      class Meta:
          indexes = [HnswIndex(name="product_emb_hnsw", fields=["embedding"],
                               m=16, ef_construction=64,
                               opclasses=["vector_cosine_ops"])]

  # query
  ProductEmbedding.objects.order_by(CosineDistance("embedding", query_vec))[:20]
  ```

- Is it worthwhile at 10k–100k products?
  - For purchase-history recommendations: no. Co-purchase neighbours come from SQL counts (section 4); vectors add nothing.
  - For content-based similarity (cold-start products with no orders, "similar products" across brands): possibly, but the hard part is producing embeddings without ML infrastructure — either a CPU sentence-embedding model inside a cron command (pulls in a heavy dependency such as PyTorch) or an external embedding API (sends only catalog text, not personal data). The project already has structured attributes and a category tree, so an attribute/category-overlap similarity in SQL is a cheaper first version.
  - If embeddings are adopted, an ANN index is still optional: 50k × 384-dimension exact scans are fast, and the cleanest design is to compute top-N neighbours nightly and write them into the same relation table with `relation_type = 'similar'`, so the serving path never touches vectors and the approximate-index filtering caveat never arises.
- Operational cost to weigh: the extension must be installed on the production PostgreSQL server (APT package) and on every developer machine — on Windows that means compiling with Visual Studio or running PostgreSQL in Docker, which is real friction for a team developing on Windows (the project environment is Windows 11). `CREATE EXTENSION` needs sufficient database privileges.

### Gaps
- The exact current pgvector-python release (0.4.2 versus 0.5.0) and its tested Django/Python matrix could not be confirmed on pypi.org.
- No benchmark of exact versus HNSW search at 10k–100k rows was collected; the "exact is enough" statement relies on the README's general note about small tables.
- Embedding-model choices for Uzbek/Russian product names were out of scope and not researched.

---

## 7. Python libraries from a cron-run management command (implicit, scikit-learn, scipy.sparse, mlxtend)

### Takeaway
All four libraries install from binary wheels on Linux and Windows and run comfortably on CPU at this scale; `implicit` 0.7.3 (May 2026) ships wheels for Windows, manylinux x86_64/aarch64 and macOS. The main pitfalls are operational (BLAS thread settings, cron environment, memory blow-ups from dense one-hot frames in `mlxtend`), and the evidence that tuned neighbourhood methods beat fancier models argues for starting with `scipy.sparse` / item-kNN rather than ALS.

### Cited Findings
- `implicit` latest release is 0.7.3 (8 May 2026); requires Python ≥ 3.9 and is tested on Python 3.9–3.14 on Ubuntu, macOS and Windows; install with `pip install implicit` or from conda-forge. — [implicit on PyPI](https://pypi.org/project/implicit/)
- Wheels are published for `win_amd64`, `manylinux2014_x86_64`, `manylinux2014_aarch64` and macOS (x86_64, arm64, universal2). GPU support is Linux-only and needs the CUDA toolkit; CPU works everywhere. — [implicit on PyPI](https://pypi.org/project/implicit/)
- Models offered: ALS, BPR, logistic matrix factorisation, and item-item nearest-neighbour models with cosine, TF-IDF or BM25 weighting. — [implicit on PyPI](https://pypi.org/project/implicit/)
- Threading pitfall: the README advises `OPENBLAS_NUM_THREADS=1` (OpenBLAS) or `MKL_NUM_THREADS=1` (MKL) because the BLAS library's own multithreading otherwise causes substantial slowdowns. — [implicit on PyPI](https://pypi.org/project/implicit/)
- `mlxtend`: Apriori becomes expensive on large catalogs because candidate itemsets explode, and low `min_support` makes it worse; FP-Growth needs no candidate generation and is a drop-in replacement (`fpgrowth`). — [mlxtend fpgrowth user guide (mirror)](https://www.aidoczh.com/mlxtend/user_guide/frequent_patterns/fpgrowth/) (via search summary)
- `mlxtend` details: `fpgrowth`/`fpmax` used to convert input to dense NumPy arrays and were later changed to work on sparse DataFrames directly; the legacy pandas `SparseDataFrame` is unsupported from mlxtend 0.17.2; boolean input columns greatly reduce validation time; Apriori's `low_memory=True` was slightly slower in the documented timing and is not a cure. — [mlxtend fpgrowth user guide (mirror)](https://www.aidoczh.com/mlxtend/user_guide/frequent_patterns/fpgrowth/) (via search summary)
- Evidence for preferring simple methods: 6 of 7 reproducible neural recommenders were beaten by tuned ItemKNN/UserKNN/P3alpha/RP3beta-style baselines; Amazon's first autoencoder lost to a bestseller list. — [Dacrema et al., ar5iv 1907.06902](https://ar5iv.labs.arxiv.org/html/1907.06902); [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Rules of ML Rule #4: keep the first model simple and get the infrastructure right, since the first model gives the biggest boost. — [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)

### Inferences
- `scipy.sparse` co-occurrence is the natural Python twin of the SQL in section 4 (background knowledge, untested sketch):

  ```python
  X = sp.csr_matrix((np.ones(len(rows), dtype=np.float32), (order_idx, product_idx)))
  X.data[:] = 1                       # binary basket matrix, orders x products
  C = (X.T @ X).tocsr()               # product x product co-purchase counts
  C.setdiag(0); C.eliminate_zeros()
  cnt = np.asarray(X.sum(axis=0)).ravel()
  # cosine = C[i, j] / sqrt(cnt[i] * cnt[j]); then top-N per row
  ```

  Memory is driven by non-zeros, not by matrix shape: 1M order lines is about 12 MB in CSR, and the product-product matrix has at most the number of distinct co-purchased pairs (a few million entries, tens of MB). This runs in seconds on one CPU core.
- `implicit`'s `CosineRecommender` / `BM25Recommender` give tuned item-kNN (with top-K truncation) in a few lines and are the right first use of the library; ALS/BPR on a small, sparse purchase matrix (most customers with one or two orders) are unlikely to beat co-occurrence plus category popularity — include them in the offline comparison only after the baselines exist.
- `mlxtend` is the wrong tool for pair recommendations over a 50k-product catalog: a dense boolean one-hot frame of 250k orders × 50k products would be about 12.5 GB. It is useful only for exploratory multi-item rules on a reduced item set (e.g. item categories instead of products, a few hundred columns).
- `scikit-learn` is useful for content-based similarity (`TfidfVectorizer` on names/attributes + `NearestNeighbors` or sparse cosine) and for metrics (`ndcg_score`), not for collaborative filtering.
- Pitfalls specific to "cron + management command":
  - Set `OPENBLAS_NUM_THREADS=1` (or the MKL variant) in the crontab line or at the very top of the command module before NumPy is imported; setting it later has no effect.
  - Cron runs with a minimal environment: use the absolute path of the virtualenv's Python, export the settings/env file explicitly, and redirect output to a log.
  - Prevent overlapping runs (advisory lock or lock file), wrap the table swap in a transaction, and exit non-zero on failure so cron mail/monitoring notices.
  - Keep explicit id maps (`product_id ↔ column index`) and fix `random_state` so results are reproducible between runs.
  - Watch peak RAM on a small VPS: never densify the matrix (`.toarray()`), load ids with `values_list(...).iterator()`, write results with `bulk_create(batch_size=...)` or `COPY`.
  - `implicit` changed its matrix-orientation convention in the 0.5 series (fit on a user×item CSR matrix) — recalled from background knowledge, **not verified this session**; check the docs for the installed version, because getting the orientation wrong silently produces nonsense.
- Dependency weight: NumPy + SciPy (+ implicit) are tens of MB of wheels with no system packages required; this is acceptable "no ML infrastructure" tooling. Deep-learning frameworks are not.

### Gaps
- No measured timings or memory figures for `implicit` ALS/BPR at this specific scale were found in sources; estimates above are reasoning from sparse-matrix sizes.
- The `implicit` documentation site (API details, orientation convention, `recommend`/`similar_items` signatures in 0.7.x) was not opened.
- Current `mlxtend`, `scikit-learn` and `scipy` version numbers and Python-version support were not checked.

---

## 8. Serving-time business rules, post-filtering and fallback chain

### Takeaway
Published system designs treat filtering and business logic as an explicit online post-processing stage after candidate retrieval; the literature also supports blending in popularity and enforcing diversity. The concrete rule set (stock, cart exclusion, durable-item suppression, variant deduplication, category caps, fallback chain, anonymous users) has to be designed locally — I found no authoritative public checklist — and this project already has the data structures needed for each rule.

### Cited Findings
- In the common recommender architecture, the online path ends with post-processing: filtering and business logic applied to retrieved/ranked candidates. — [Eugene Yan, System Design for Recommendations and Search](https://eugeneyan.com/writing/system-design-for-discovery/)
- Amazon generates candidates by merging the related-item lists of the customer's recent purchases and names "when to recommend" (e.g. reminding to reorder consumables such as diapers) as an open research direction. — [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- With no information about the user, the most popular items are the default recommendation. — [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Diversity has measured online value: at Yahoo! Answers, diversified recommendations gave +17% answers and +10% session length (Szpektor et al.); conversely a DVD retailer's recommender reduced aggregate sales diversity (Lee & Hosanagar 2019). — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Netflix mixes a substantial share of unpersonalised popularity into its ranking. — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Project context: `Product.is_active` is the only availability flag with logic; stock is `Product.quantity` plus per-branch `ProductRemaining`; variants are grouped by `ProductVariantGroup` / `ProductVariantItem`; carts and favourites are keyed by customer or by `cart_token` / `favourite_token` cookies; `RecentlyViewedProducts` exists; product lists should be built with `get_optimized_product_qs`; the catalog hierarchy is category → sub category → item category → product. — repository `CLAUDE.md`

### Inferences
- Serving pipeline (my design): over-fetch candidates (3–5 × the slots needed) → hard filters → deduplicate → diversify → fill from fallback chain → load products through `get_optimized_product_qs` preserving order → log the impression.

  ```python
  def recommend(seeds, customer, anon_token, placement, n):
      cands = merged_candidates(seeds, limit=5 * n)              # cached ids + scores
      cands = only_active_in_stock(cands)                        # is_active, quantity > 0
      cands = drop(cands, cart_product_ids(customer, anon_token))
      cands = drop(cands, seeds)
      cands = drop(cands, recently_bought_durables(customer))    # see below
      cands = one_per_variant_group(cands)                       # keep best-scored variant
      cands = cap_per_item_category(cands, max_per_category=2)
      level = 0
      while len(cands) < n and level < len(FALLBACKS):
          cands += FALLBACKS[level](seeds, exclude=cands); level += 1
      return cands[:n], level
  ```

- Rules and how to implement each here:
  - **Active and in stock:** filter on `is_active` and `quantity > 0` at request time (not in the nightly job — stock changes during the day). For pickup-oriented flows, consider branch stock.
  - **Already in cart / the seed itself:** always exclude. Already-favourited items can stay.
  - **Recently purchased durables:** people re-buy cement, paint, fasteners and consumables but not a second drill next week. Derive a per-item-category "repeat rate" from order history (share of buyers who bought the same category again within N days). Low-repeat categories → suppress products (and optionally the whole item category) the customer bought in the last X months; high-repeat categories → do the opposite and surface a "buy again" block.
  - **Variant deduplication:** at most one product per variant group in a list, and never recommend another variant of the seed product in a "bought together" slot (other sizes/colours belong to the variant selector, not to cross-sell).
  - **Diversity:** cap N per item category (and optionally per brand); for "bought together" prefer items from *other* item categories than the seed (complements), for "similar" prefer the same item category (substitutes). Storing the two as separate relation types keeps this explicit.
  - **Fallback chain:** item-level co-purchase → item-category-level co-purchase (the same SQL as section 4 but aggregated on item category, then that category's bestsellers) → popular in the seed's item category / sub category → global bestsellers. Record `fallback_level` in the impression log; a high fallback share is the signal that coverage, not ranking, is the problem.
  - **Minimum quality:** if fewer than a minimum number of items survive (e.g. < 4), hide the widget rather than show a thin or obviously generic list — the project's home blocks already use a `min_products` rule of the same kind.
  - **Anonymous users:** seeds = current product, cookie cart, recently viewed, favourites (all token-keyed already). On login, merge token history into the customer's seeds. Bucket experiments by the same token.
  - **Merchandising overrides:** a small manual "pinned / blocked related products" table that takes precedence over computed relations is cheap and handles embarrassing pairs.
- Apply rules after the cache read: caching the post-filter list per user would need invalidation on every stock or cart change.

### Gaps
- No authoritative public source (paper or engineering blog) was found that enumerates serving-time business rules for e-commerce recommenders; this section is mostly design reasoning on top of the cited architecture.
- No data on appropriate "do not re-recommend" periods for building-materials categories was found; the repeat-rate approach must be calibrated on the store's own orders.

---

## 9. Bestsellers and trending with time decay; feedback loops and popularity bias

### Takeaway
A time-decayed popularity score is both the mandatory baseline and the last step of every fallback chain; exponential decay (a half-life parameter) can be computed either incrementally (store a "temperature" and a timestamp) or, at this scale, simply recomputed in one SQL statement from recent order lines. Recommenders feed their own popularity statistics, so sales caused by recommendations should be identifiable in the logs and popularity should be normalised within categories.

### Cited Findings
- Exponential-decay "hotness" (Newton's law of cooling): current temperature = last temperature × exp(−cooling rate × hours since last update). Store only each item's temperature and last-update time; on each new event compute the current temperature, add a fixed increment and save; sorting needs no writes and the event history never has to be reprocessed. — [Evan Miller, Rank Hotness With Newton's Law of Cooling](https://www.evanmiller.org/rank-hotness-with-newtons-law-of-cooling.html) (older article; the method is timeless)
- The cooling rate is chosen from the number of hours in which the score should fall by about half; a smaller rate lets popular items linger; parameters are a judgment call that can be tuned by A/B testing, and exponential decay prevents extremely popular items from staying on top forever. — [Evan Miller](https://www.evanmiller.org/rank-hotness-with-newtons-law-of-cooling.html)
- A time-decayed popularity list is used as the reference baseline in field studies (Forbes.com: a hybrid method gained 37% CTR over a time-decayed popularity baseline; Google News: personalisation gained about 38% clicks over popularity; YouTube: co-visitation gained more than 200% CTR over most-viewed). — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Popularity-heavy recommendations can inflate CTR while creating feedback loops and reduced diversity; in one retailer study recommendations decreased aggregate sales diversity (Gini) and niche items lost share (Lee & Hosanagar 2019), while Netflix reports increased exploration measured by "effective catalog size". — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Raw co-purchase counts make bestsellers the top related item for everything; normalising by expected co-occurrence removes that bias. — [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- The cyclic (feedback) nature of recommendation is listed as an open evaluation challenge. — [Castells & Moffat, AI Magazine 2022](https://ojs.aaai.org/index.php/aimagazine/article/view/21745) (abstract, via search summary)
- Project context: a `bestsellers` home block already ranks by units sold; auto badges support a `sales_30d` rule and are recalculated by a cron command every 15 minutes. — repository `CLAUDE.md`

### Inferences
- Batch formulation (mine, untested; half-life H days gives rate ln 2 / H):

  ```sql
  SELECT oi.product_id,
         p.product_item_category_id,
         sum(exp(-ln(2) * extract(epoch FROM now() - o.created_at) / 86400.0 / 30)) AS score  -- H = 30 days
  FROM service_orderitem oi
  JOIN service_order o   ON o.id = oi.order_id AND o.status <> 4
  JOIN service_product p ON p.id = oi.product_id
  WHERE o.created_at >= now() - interval '180 days'
  GROUP BY 1, 2;
  ```

  Count each (order, product) once — i.e. decayed number of orders or of distinct customers — rather than summing `quantity`: in building materials one contractor order of 500 bags would otherwise define the "bestseller". Store `score` with rank within item category, sub category and globally in one small table; rebuild nightly (or hourly, it is cheap).
- "Trending" as distinct from "bestseller": ratio of a short window to a longer baseline with smoothing, e.g. (orders in last 7 days + a) / (orders in previous 28 days / 4 + a); require a minimum absolute count so that 0 → 2 orders does not "trend".
- Half-life choice: long (30–60 days) for bestsellers so the list is stable and seasonal shifts still register; short (3–7 days) for trending. With modest volume, a very short half-life produces noisy lists.
- Incremental "temperature" updates (Evan Miller's scheme) are unnecessary at this volume but are the right design if the score should react within minutes; they also fit Redis `ZINCRBY` if needed later.
- Avoiding feedback loops and popularity bias:
  1. Tag purchases that came through a recommendation click (section 3) and either exclude or down-weight them when computing popularity and co-purchase, so that the widget does not vote for itself.
  2. Use category-normalised popularity and expected-count-normalised relations (lift/cosine, not raw counts) for item-to-item lists.
  3. Reserve one or two slots for exploration (random eligible item from the next-best candidates or a new product in the same item category) and log them with their own `algorithm` label.
  4. Monitor coverage@K and the exposure share of the top 1% of products over time; a rising concentration is the symptom.
  5. Keep the long-running holdout group — its behaviour is unaffected by the loop and gives clean data.

### Gaps
- No quantitative guidance on half-life values for DIY/building-materials retail was found; values above are starting points.
- Evan Miller's article contains no SQL; the SQL is mine.
- No source was fetched that measures the effect of excluding recommendation-driven sales from popularity statistics.

---

## 10. Privacy / legal: using purchase history for personalisation; Uzbekistan Law No. ZRU-547

### Takeaway
Purchase history tied to a customer is personal data under Uzbekistan's Law "On Personal Data" (ZRU-547, 2 July 2019), which is consent- and purpose-based and historically required storing citizens' data on servers in Uzbekistan (Article 27-1); a March 2026 amendment relaxed strict localisation for most data categories under conditions, but details and secondary rules are still settling. Computing recommendations in-house on servers located in Uzbekistan avoids the cross-border question entirely; sending customer-level purchase data to a foreign recommendation SaaS requires a specific legal check. This is orientation, not legal advice.

### Cited Findings
- The Law of the Republic of Uzbekistan "On Personal Data" No. ZRU-547 of 2 July 2019 is the core data-protection act, with consent, security, registration and (since its introduction) data-localisation obligations. — [Legal 500 / SETTLE, Personal data compliance in Uzbekistan (7 August 2025)](https://www.legal500.com/developments/thought-leadership/personal-data-compliance-in-uzbekistan/)
- Consent must be obtained in a form that lets the operator prove it was given (Art. 21(1)); for biometric, genetic or health data it must be written (Art. 21(2)). Consent should state the operator, the subject, the purposes, the list of data, the term, and whether third-party transfer, cross-border transfer or public disclosure is allowed. — [Legal 500 / SETTLE](https://www.legal500.com/developments/thought-leadership/personal-data-compliance-in-uzbekistan/)
- A data subject can withdraw consent at any time; the operator must then stop the processing and delete the data unless another legal basis applies (Art. 17). — [Legal 500 / SETTLE](https://www.legal500.com/developments/thought-leadership/personal-data-compliance-in-uzbekistan/)
- Purpose limitation: collection must be proportionate to the declared purposes (Art. 10(2)); processing beyond the originally declared purposes requires a new, separate consent (the article cites Arts. 14(2) and 15(3)). — [Legal 500 / SETTLE](https://www.legal500.com/developments/thought-leadership/personal-data-compliance-in-uzbekistan/)
- As of the August 2025 article, Article 27-1 required personal data of Uzbek citizens to be stored on servers physically located in Uzbekistan. — [Legal 500 / SETTLE](https://www.legal500.com/developments/thought-leadership/personal-data-compliance-in-uzbekistan/)
- Personal-data databases must be registered before processing starts (Art. 20; Cabinet of Ministers Resolution No. 71); the State Personalization Center under the Cabinet of Ministers is the authorised body and decides within up to 15 days; exemptions exist (among others internal-use data, public data, basic identity details, non-automated processing). — [Legal 500 / SETTLE](https://www.legal500.com/developments/thought-leadership/personal-data-compliance-in-uzbekistan/)
- Cross-border transfer (Art. 15) is allowed to states with adequate protection; otherwise it needs the subject's consent or a legal/treaty ground; no official list of adequate countries had been published as of that article. — [Legal 500 / SETTLE](https://www.legal500.com/developments/thought-leadership/personal-data-compliance-in-uzbekistan/); [Mondaq, Uzbekistan enacts first data protection law](https://www.mondaq.com/data-protection/828474/uzbekistan-enacts-first-data-protection-law) (the latter via search summary)
- Liability: administrative fines under Article 46-2 of the Code of Administrative Liability and criminal liability under Article 141-2 of the Criminal Code for serious violations; the article gives no amounts. — [Legal 500 / SETTLE](https://www.legal500.com/developments/thought-leadership/personal-data-compliance-in-uzbekistan/) (article numbers as rendered by the source; verify on lex.uz)
- 2026 amendment: the President signed amendments to the personal data law on 26 March 2026 (adopted by the Legislative Chamber in January and the Senate in February), aimed at enabling services such as Apple Pay, Google Pay and PayPal; strict localisation was narrowed so that most personal data may be stored on foreign servers under conditions. — [Kun.uz, 27 March 2026](https://kun.uz/en/news/2026/03/27/uzbekistan-amends-personal-data-law-to-facilitate-global-payment-systems) (via search summary; the article body could not be fetched directly)
- According to Dentons, the amendments took effect on 27 March 2026 and dismantle the strict regime under which, since 2021, Uzbek nationals' personal data had to be collected, systematised and stored on technical means physically located in Uzbekistan (Article 27-1). — [Dentons, 31 March 2026](https://www.dentons.com/en/insights/articles/2026/march/31/uzbekistan-dismantles-strict-data-localization-regime) (via search summary; direct fetch returned HTTP 403)
- Data that must still be stored and processed only in Uzbekistan after the amendment: biometric data, genetic data, and personal data of users of telecom operators active in Uzbekistan. — [Kun.uz](https://kun.uz/en/news/2026/03/27/uzbekistan-amends-personal-data-law-to-facilitate-global-payment-systems); [Settle Advisory](https://settleadvisory.com/news-en/localization-of-personal-data-in-uzbekistan-transition-to-a-more-flexible-regulatory-model/) (both via search summary)
- Reported conditions for storing other personal data abroad: the destination state is recognised as providing adequate protection (list compiled by the Cabinet of Ministers), or the operator adopts standard contractual clauses / binding corporate rules meeting requirements approved by the authorised body. — [Kun.uz](https://kun.uz/en/news/2026/03/27/uzbekistan-amends-personal-data-law-to-facilitate-global-payment-systems) (via search summary; at least one further condition was truncated in the material I could see)

### Inferences
- Behavioural data (orders, carts, favourites, recently viewed) linked to a customer id or phone number is personal data; cookie-token histories become personal data once they can be linked to a customer (which happens at login when token data is merged).
- Personalised recommendations are a distinct processing purpose. The privacy policy / consent text shown at registration should explicitly cover "use of order and browsing history to personalise product suggestions"; if the existing consent text does not, purpose limitation suggests updating it (and, for existing customers, obtaining consent to the new purpose). A simple "personalised recommendations: on/off" setting plus falling back to non-personal lists (popular in category) is the low-risk design, and it reuses the fallback chain that must exist anyway.
- In-house design choices that keep the legal surface minimal: compute everything inside the existing PostgreSQL on servers in Uzbekistan; do not export customer-level data to foreign analytics or recommendation SaaS; item-to-item tables and bestseller lists are aggregates over products, not personal data, once computed; keep the recommendation event log covered by the same retention and deletion process as other customer data (delete or anonymise on account deletion / consent withdrawal).
- If a foreign SaaS is ever considered (hosted recommender, product analytics, embedding APIs): sending *catalog* data (product names, attributes) is not a personal-data transfer; sending customer-level events is a cross-border transfer that, after March 2026, appears possible under the adequacy/SCC conditions — but the adequacy list and the SCC requirements need to be confirmed as actually issued before relying on them.
- Even where not strictly required, avoid sensitive inferences in widget copy (e.g. "because you bought X" on a shared device) and keep "because you bought" explanations to non-sensitive categories — a trust consideration more than a legal one in this product domain.

### Gaps
- The official consolidated text of ZRU-547 on lex.uz was not opened; all article numbers come from law-firm summaries and should be verified.
- The amending law's number is inconsistent across sources (some name it ZRU-1125 of 26 March 2026; this was not confirmed), and the full list of conditions for foreign storage, the status of the Cabinet's adequacy list, and any changes to database registration (Art. 20) could not be verified because the Dentons article was inaccessible.
- Whether the law contains specific rules on profiling / automated decision-making was not established; the fetched summary did not mention any.
- Penalty amounts were not found.
- Whether registration of the store's customer database in the State Register is already in place is a project fact I cannot determine.

---

## 11. Published incremental-rollout playbooks: what to build in which order

### Takeaway
The published guidance is consistent: launch with heuristics and instrumentation first (Rules of ML #1–#2), make the first model simple and get the pipeline right (#4), prefer batch over real-time until batch is shown to be insufficient (Eugene Yan), and use the offline-table + online-merge item-to-item design that Amazon ran for two decades. For this store that means: logging and popularity baselines → SQL co-purchase table → on-request personal merge → controlled measurement → only then consider matrix factorisation or embeddings.

### Cited Findings
- Rule #1: "If machine learning is not absolutely required for your product, don't use it until you have data." Simple heuristics (e.g. ranking by install counts) get a product much of the way. — [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- Rule #2: design and implement metrics first — track as much as possible in the current system and build the experiment framework early. Rule #3: once there is data, prefer a learned model over a complex, unmaintainable heuristic. Rule #4: keep the first model simple and get the infrastructure right; the first model gives the biggest boost. Rule #5: test the infrastructure separately from the ML. — [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- Rules #12–#13: choose a first objective that is simple, observable and attributable (e.g. was the ranked item clicked), as a proxy for the true objective. — [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- Eugene Yan: structure the system as offline/online × retrieval/ranking; start with candidate retrieval and add a ranker later; before building real-time retrieval and ranking, check whether batch recommendations are good enough. — [Eugene Yan, System Design for Recommendations and Search](https://eugeneyan.com/writing/system-design-for-discovery/)
- Amazon's item-to-item architecture (daily offline related-items table, online merge for the visitor's recent purchases) received IEEE Internet Computing's test-of-time recognition and was explicitly chosen for computational cheapness as well as quality. — [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Field evidence that the purchase-based simple method is where the value is: purchase-based collaborative filtering lifted DVD sales by 35% while view-based did not show a significant effect; YouTube's co-visitation beat most-viewed by more than 200% CTR. — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Test UI/placement together with algorithms, since presentation changes alone can double CTR. — [Jannach & Jugovac](https://ar5iv.labs.arxiv.org/html/1908.08328)
- Booking.com's conclusion after about 150 models: business impact comes from an iterative, hypothesis-driven process validated by randomised experiments, not from offline model quality alone. — [Colyer's summary](https://blog.acolyer.org/2019/10/07/150-successful-machine-learning-models/) (via search summary)
- Tuned simple baselines beat most published neural recommenders. — [Dacrema et al., ar5iv 1907.06902](https://ar5iv.labs.arxiv.org/html/1907.06902)

### Inferences
- Suggested build order for this project (each stage shippable on its own; everything is a Django model + a cron-run management command + one client endpoint):
  1. **Instrumentation and plumbing (no recommendations yet).** Recommendation event table and `rec_request_id` flow (section 3); stable bucketing function (hash of customer id / cookie token) with a permanent holdout; one generic endpoint shape `GET recommendations/?placement=&product=` returning products plus `rec_request_id`.
  2. **Heuristic lists (Rule #1).** Time-decayed bestsellers per item category / sub category / global (section 9); "similar products" from item category + brand + shared attribute values. Ship widgets on the product page and cart using these, with full business-rule filtering (section 8). This already produces impression/click data and the baseline to beat.
  3. **Offline evaluation harness.** A management command that does the temporal split and prints HitRate@K / NDCG@K / coverage for popularity, category popularity and any candidate method (section 1).
  4. **Co-purchase item-to-item table** via nightly SQL (section 4), stored with relation type and scores (section 5); "bought together" on the product page and cart/checkout; category-level co-purchase as the first fallback.
  5. **Personal block** ("for you" / "buy again") by merging item-to-item lists for last purchases, cart and recently viewed on request (section 5), plus durable/consumable rules.
  6. **Measurement.** Holdout comparison over several weeks; A/B or interleaving between ranking variants on widget add-to-cart rate; guardrails (section 2).
  7. **Only if evidence supports it:** item-kNN/ALS via `implicit` in the same nightly command, embeddings + pgvector for cold-start similarity, a learned re-ranker. Each new method must beat stage 2–4 baselines offline and then online.
- The existing project structures map well onto this: a home-page block type could later host a personal block, the `bestsellers` block and `sales_30d` badge rule already compute sales-based popularity, and cron-run commands are an established pattern.

### Gaps
- No engineering blog post from a small or medium-size shop describing a concrete staged recommender rollout with numbers was found in this session; the cited playbooks come from large companies (Google, Amazon, Alibaba, Booking.com) and from Eugene Yan's survey of them.
- Eugene Yan's other relevant posts (e.g. on real-time recommendations and on beating baseline recommenders) were not opened.
