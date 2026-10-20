# Classic (non-deep-learning) product recommendation algorithms from purchase history — what works on small / sparse e-commerce data (state of practice, 2026)

Research date: 2026-10-10. Reader context: Django + PostgreSQL + Redis store, tens of thousands of SKUs, modest order volume, cron batch jobs, no ML infrastructure.

Source-quality legend used below: **[primary]** = original paper / official docs read in this session; **[vendor blog]** = commercial blog, treat as opinion; **[search summary]** = taken from a search-result summary, page not opened in full (lower confidence). Statements under "Inferences" are my own reasoning or background knowledge and are **not** sourced.

Out of scope (one-line pointer): deep / sequential / LLM recommenders are covered by another researcher; the only relevant data point here is that at Amazon a 2014 autoencoder for Prime Video first lost to both item-to-item CF and a plain bestseller list, and only won (about 2x) after the training data was split chronologically — [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm).

---

## 1. Co-purchase / "frequently bought together": co-occurrence counts vs. association rules; which score to rank by; popularity bias; thresholds

### Takeaway
For pair recommendations ("bought together") plain pairwise co-occurrence counting plus a normalised score is the whole algorithm; Apriori / FP-Growth / Eclat only add value when rules with multi-item antecedents are wanted, and they are driven by a minimum-support threshold that is hard to satisfy on a large, sparse catalog. Raw counts and confidence favour bestsellers, pure lift / PMI over-promotes rare coincidences, so practice is a normalised score (Jaccard, cosine, lift, or a significance test such as LLR) **combined with a minimum co-occurrence / support floor**.

### Cited Findings

**Metric definitions (association rules A → C)**
- support = share of transactions containing A ∪ C; confidence = P(C | A), asymmetric (A→C differs from C→A), equals 1 when C always accompanies A; lift = how much more often A and C occur together than under independence, exactly 1 when independent; leverage = observed joint frequency minus the frequency expected under independence, 0 = independence; conviction = degree to which the consequent depends on the antecedent, 1 = independence, infinite at confidence 1. — [mlxtend association_rules docs, primary](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/)
- mlxtend also computes Zhang's metric (−1…1, sign = association vs. dissociation), Jaccard (0…1), certainty (−1…1, 0 = independence) and Kulczynski (0…1, near 0.5 = uninteresting). — [mlxtend association_rules docs](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/)
- The example thresholds in the mlxtend docs are confidence ≥ 0.7 and lift ≥ 1.2 (illustrative on a toy dataset, not a recommendation for retail). — [mlxtend association_rules docs](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/)

**Apriori vs. FP-Growth (and what mlxtend ships)**
- FP-Growth needs no candidate generation, builds an FP-tree, and is described as potentially orders of magnitude faster than Apriori and attractive for large datasets; on the doc's toy dataset the measured timings are 850 µs (Apriori) vs. 320 µs (FP-Growth), i.e. about 2.7x. — [mlxtend fpgrowth docs, primary](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/fpgrowth/)
- mlxtend's frequent-pattern functions expect a **one-hot encoded pandas DataFrame** (transactions × items, 0/1 or True/False); `min_support` defaults to 0.5; `max_len` caps itemset length. The docs sidebar lists Apriori, FP-Growth, FP-Max and association_rules — no Eclat. — [mlxtend fpgrowth docs](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/fpgrowth/)

**Popularity bias and how each score behaves**
- Amazon's own account: simple co-purchase counts would surface bestsellers for everyone, so the original relatedness measure was differential — B is related to A if buyers of A are more likely to buy B than the average customer. — [Amazon Science, history of the recommendation algorithm](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Amazon later found a flaw in that measure: buyers of A tend to be heavier buyers overall, so the baseline probability of also buying B was systematically underestimated; the fix discounts heavy buyers according to their overall purchase volume, and Amazon describes it as a large quality improvement. — [Amazon Science](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Microsoft's SAR (Simple Algorithm for Recommendation) offers three pair scores from the co-occurrence matrix C (c_ii = item frequency): **counts** s_ij = c_ij (favours predictability — popular items recommended most of the time); **lift** s_ij = c_ij / (c_ii · c_jj) (favours discoverability / serendipity); **Jaccard** s_ij = c_ij / (c_ii + c_jj − c_ij) (a compromise between the two). The deep-dive notebook itself uses Jaccard. — [Microsoft Recommenders, SAR deep dive, primary](https://raw.githubusercontent.com/recommenders-team/recommenders/main/examples/02_model_collaborative_filtering/sar_deep_dive.ipynb)
- Worked example of confidence misleading: bread and milk look strong on support and confidence, yet lift is 0.96 because each is in 62.5% of baskets. — [Statology tutorial, search summary](https://www.statology.org/how-to-calculate-support-confidence-and-lift-in-python/)
- Lift's own failure mode: rare itemsets can produce enormous lift values and lift is noisy on small databases (the article attributes this to the R `arules` documentation); a high lift on a low-support pair is usually noise. The same article warns that confidence rises with the popularity of the predicted item and that co-occurrence is neither preference, complementarity nor causation. — [Koji, "Market Basket Analysis in 2026", vendor blog, Aug 2026](https://www.koji.so/blog/market-basket-analysis-guide-2026)
- PMI has the same weakness as lift: it is sensitive to the marginals and gives inflated scores to sparser events. — [arXiv 2203.08089 "On Suspicious Coincidences and Pointwise Mutual Information", search summary](https://arxiv.org/pdf/2203.08089)
- Log-likelihood ratio (LLR): Dunning's 1993 paper argues likelihood-ratio tests give good results on relatively small samples where normal-approximation statistics fail on rare events. — [Dunning 1993, Computational Linguistics, search summary](https://preview.aclanthology.org/moar-dois/J93-1003.pdf)
- Apache Mahout's item-similarity / co-occurrence recommender uses LLR to decide which co-occurrences are anomalous enough to be kept as indicators (2×2 table: both, A only, B only, neither); its docs say the other similarity measures of the legacy job were being deprecated in favour of LLR because it performed best in practice. — [Mahout docs, search summary](https://mahout.apache.org/Map_Reduce_Folder/basics/collocations.html) (the Spark co-occurrence tutorial URL returned 404 on direct fetch, so this is from the search summary only)
- Vendor practice: a commerce search vendor reports switching its "Frequently Bought Together" block from raw popularity to lift ranking, noting it also favours complements over same-category near-duplicates. — [Layers changelog, vendor, search summary](https://www.uselayers.com/changelog/smarter-ranking-for-interaction-recommendations)

**Thresholds cited in practice**
- Minimum support "around 0.01 to 0.05 on retail data"; pairs below roughly 0.01 support to be treated with suspicion. — [Koji, vendor blog](https://www.koji.so/blog/market-basket-analysis-guide-2026) (grocery-style framing; see Inferences for why this does not transfer to a 10k+ SKU catalog)
- Google's managed "Frequently Bought Together" model requires at least 1,000 purchase-complete events, an average of 10 purchase events per catalog item over a 1-year window (or 90 days of purchase events in the last year), and at least 100 unique catalog items with purchases. — [Google Vertex AI Search for commerce, create-models, primary](https://docs.cloud.google.com/retail/docs/create-models)
- Google also instructs not to flatten multi-item baskets into separate purchase events — the basket is the unit for FBT. — [Google Vertex AI Search for commerce, user events](https://docs.cloud.google.com/retail/docs/user-events)

### Inferences
- Standard formulas (not rendered by the fetch tool, stated from standard definitions): support(A→C) = P(A∪C); confidence = P(A∪C)/P(A); lift = P(A∪C)/(P(A)·P(C)); leverage = P(A∪C) − P(A)P(C); conviction = (1 − P(C))/(1 − confidence); PMI = log(lift); cosine = c_ij / sqrt(c_ii·c_jj); Jaccard = c_ij / (c_ii + c_jj − c_ij). SAR's "lift" is the same quantity as rule lift up to the constant factor N (number of baskets), so ranking by it is identical.
- For an item→items widget, association-rule mining restricted to 1-item antecedents and 1-item consequents *is* pairwise co-occurrence counting. On a catalog of tens of thousands of SKUs a relative support of 0.01 means "in 1% of all orders", which almost no pair reaches; a workable floor is an **absolute count** (e.g. the pair appears in at least 3–5 distinct orders / customers) rather than a relative support. Apriori/FP-Growth with a one-hot DataFrame (orders × 30k columns) is also memory-hungry for no gain; a SQL self-join on `OrderItem` (GROUP BY product pair) or a sparse `X.T @ X` in scipy does the same job.
- Ranking recipe consistent with the sources: (1) count pair co-occurrences over orders (or over customer histories within a time window), (2) drop pairs under the minimum count, (3) rank by a popularity-corrected score — cosine or Jaccard as the safe default, LLR if a significance-style filter is wanted, lift only together with the count floor or with shrinkage (e.g. c_ij / (c_ii·c_jj + k)); (4) confidence is the right number to *show* ("X% of buyers of A also bought B") but a poor one to rank by.
- Direction matters for building materials (primer → paint is not paint → primer in the same strength): confidence is asymmetric, cosine/Jaccard/lift are symmetric. An asymmetric variant (confidence divided by a power of the consequent's popularity, "asymmetric cosine") keeps direction while damping bestsellers.
- Amazon's heavy-buyer correction is directly relevant to a store with professional buyers (the `prorab` role): a contractor's large mixed baskets co-occur with everything. Cheap equivalents: cap or down-weight very large baskets (weight each pair by 1/(basket size − 1) or 1/log(1+n)), or count each customer once per pair.
- Same-order co-occurrence gives *complements* (FBT); co-occurrence across a customer's different orders or across views gives more *substitutes / "also bought"*. They should be separate tables.

### Gaps
- No engineering blog from a large retailer with concrete production thresholds (minimum pair count, lift cut-off) was found in this session; the threshold figures above come from a vendor blog and from Google's managed-service minimums.
- Eclat was not sourced (no mature, maintained Python implementation was confirmed; mlxtend does not ship it).
- The exact corrected relatedness formula from Smith & Linden 2017 (IEEE Internet Computing 21(3):12–18) could not be read — the paper PDF is paywalled; only Amazon's own summary article was available.
- Mahout LLR details (downsampling defaults, cross-occurrence of views with purchases) could not be verified from the primary page (404).

---

## 2. Item-to-item collaborative filtering (Amazon 2003; 2017 retrospective)

### Takeaway
Item-to-item CF precomputes, offline, a "similar items" table from which customers bought which items, and at request time only looks up the neighbours of the items the customer already has — so serving cost depends on the size of the customer's history, not on catalog or customer count. It was designed precisely for customers with very few purchases, which makes it the natural core method for a sparse store.

### Cited Findings
- Algorithm (2003 paper): for each catalog item I1, for each customer C who bought I1, for each item I2 bought by C, record that a customer bought both; then compute a similarity between I1 and each such I2. The similarity suggested is the cosine between item vectors whose dimensions are customers. — [Linden, Smith, York 2003, IEEE Internet Computing, primary (PDF read)](https://www.cs.umd.edu/~samir/498/Amazon-Recommendations.pdf)
- Offline cost: worst case O(N²M) (N items, M customers), in practice closer to O(NM) because most customers have very few purchases; sampling the customers who buy best-selling titles cuts the runtime further with little quality loss. — [Linden et al. 2003](https://www.cs.umd.edu/~samir/498/Amazon-Recommendations.pdf)
- Online: given the similar-items table, the algorithm aggregates the neighbours of each of the user's purchased/rated items and recommends the most popular or most correlated ones; the cost depends only on the number of items the user has bought or rated, independent of catalog size and customer count. — [Linden et al. 2003](https://www.cs.umd.edu/~samir/498/Amazon-Recommendations.pdf)
- Sparse-user claim: unlike traditional CF, it produces good recommendations from as few as two or three items. — [Linden et al. 2003](https://www.cs.umd.edu/~samir/498/Amazon-Recommendations.pdf)
- Difference from user-based CF: traditional (user-based) CF represents each customer as an N-dimensional item vector (often scaled by inverse item frequency so that bestsellers count less), finds the most similar customers by cosine and recommends what they bought; it does little offline work, its online cost scales with customers and catalog, and it degrades when a customer has few purchases. Cluster models move work offline but compare a user to coarse segments, so quality is poor; search/content-based methods return items that are either too general or too narrow. — [Linden et al. 2003](https://www.cs.umd.edu/~samir/498/Amazon-Recommendations.pdf)
- Scale at the time of the paper: more than 29 million customers and several million catalog items; the paper notes most published algorithms had been evaluated on datasets about three orders of magnitude smaller (MovieLens 35,000 customers / 3,000 items). — [Linden et al. 2003](https://www.cs.umd.edu/~samir/498/Amazon-Recommendations.pdf)
- 2017 retrospective: "Two Decades of Recommender Systems at Amazon.com" by Brent Smith and Greg Linden, IEEE Internet Computing 21(3), 2017; the 2003 paper was honoured in 2017 by the journal as the paper that best withstood the test of time. — [Amazon Science publication page](https://www.amazon.science/publications/two-decades-of-recommender-systems-at-amazon-com); [Amazon Science history article](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Why Amazon kept it: item-level analysis gave better recommendations than customer-level matching and was computationally cheaper — daily related-item lists for every product were feasible with early-2000s hardware; the index has to be refreshed regularly because purchase histories change quickly. — [Amazon Science history article](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Refinement of the similarity (relatedness) score over the years: from raw co-purchase counts → "more likely than the average customer" → correction for heavy buyers (see section 1). — [Amazon Science history article](https://www.amazon.science/the-history-of-amazons-recommendation-algorithm)
- Similarity choices used for item-KNN in reproducibility work: Jaccard, cosine, asymmetric cosine, Dice–Sørensen and Tversky, with a **shrink term** (reported to sometimes give substantial gains), neighbourhood size, and optional TF-IDF or BM25 weighting of the interaction matrix as tuned hyperparameters. — [Ferrari Dacrema et al., "A Troubling Analysis…", TOIS, primary](https://ar5iv.labs.arxiv.org/html/1911.07698)
- The `implicit` library implements item-item nearest-neighbour models with cosine, TF-IDF or BM25 weighting; its tutorial applies `bm25_weight(..., K1=100, B=0.8)` to reduce the impact of heavy repeat users and to reduce the weight of popular items. — [implicit GitHub](https://github.com/benfred/implicit); [implicit tutorial](https://benfred.github.io/implicit/tutorial_lastfm.html)

### Inferences
- "Frequently bought together" (section 1) and item-to-item CF are the same computation over different co-occurrence units: order-level baskets vs. whole customer histories. One batch job can produce both tables.
- For a personalised block ("recommended for you"), the item-to-item recipe is: take the customer's recent purchased / carted / viewed products, union their precomputed neighbour lists, sum the similarity scores (optionally weighted by recency and event type), remove items already bought, apply business filters (`is_active`, in stock). This is exactly Microsoft SAR's A × S scoring (section 6) and needs no model training.
- At this store's scale the offline job is trivial: with tens of thousands of orders and a few items per order the pair count is at most a few million rows; it fits a nightly cron job in pure SQL or scipy, with results stored in a PostgreSQL table (product_id, related_id, score, rank) and/or cached in Redis.
- User-based CF is a poor fit here: with 1–3 orders per customer, user–user overlap is nearly empty, and neighbours must be recomputed as users change. No source in this session recommends it for sparse e-commerce.

### Gaps
- The technical content of the 2017 paper (time-aware relatedness, compatibility / directionality of purchases, category-specific tuning) could not be read directly; only Amazon's summary article was available.
- No quantified share of Amazon sales attributable to recommendations was found in a primary source in this session (the frequently repeated "35%" figure was not verified and is not used here).

---

## 3. Matrix factorization for implicit feedback (ALS, BPR, logistic MF) and strong linear baselines (EASE, SLIM, item-KNN); what reproducibility studies say

### Takeaway
ALS (Hu/Koren/Volinsky), BPR and EASE are the mature "learned" classics; reproducibility studies consistently find that well-tuned simple methods (item-KNN, graph-based P3α/RP3β, SLIM, EASE, iALS) match or beat most published neural models — and on small, very sparse datasets even plain popularity can win. For a sparse store this argues for starting with co-occurrence / item-KNN and treating MF and EASE as optional second steps.

### Cited Findings

**Implicit ALS (Hu, Koren, Volinsky 2008)**
- Model: raw observations r_ui (e.g. purchase counts) are split into a binary preference p_ui (1 if r_ui > 0, else 0) and a confidence c_ui = 1 + α·r_ui; α = 40 worked well in their experiments; a log variant c_ui = 1 + α·log(1 + r_ui/ε) is also proposed. — [Hu, Koren, Volinsky 2008, primary (PDF read)](http://yifanhu.net/PUB/cf.pdf)
- Objective: weighted squared error over **all** user–item pairs (unobserved pairs count as preference 0 with low confidence) plus L2 regularisation; solved by alternating least squares; running time O(f²·𝒩 + f³·m) per user sweep (𝒩 = non-zero observations, m users, f factors), i.e. linear in the data size; typical f is 20–200; about 10 sweeps. — [Hu et al. 2008](http://yifanhu.net/PUB/cf.pdf)
- Implicit-feedback properties the paper lists: no negative feedback, inherently noisy (a purchase may be a gift or a disappointment), the numeric value expresses confidence rather than preference, and evaluation needs recall-oriented measures. — [Hu et al. 2008](http://yifanhu.net/PUB/cf.pdf)
- Evaluation setting: about 300,000 set-top boxes, about 17,000 programs, about 32 million non-zero observations over 4 weeks; a popularity ranking is described as a surprisingly powerful baseline; the neighbourhood baseline that worked best used cosine similarity and *all* items as neighbours. — [Hu et al. 2008](http://yifanhu.net/PUB/cf.pdf)
- Explanations: the factor model can be rewritten as a linear function of the user's past actions weighted by a user-specific item–item similarity, so "because you bought X" explanations are possible. — [Hu et al. 2008](http://yifanhu.net/PUB/cf.pdf)

**BPR (Rendle et al. 2009)**
- BPR-Opt is a generic pairwise ranking criterion (maximum posterior estimator) for implicit feedback such as clicks and purchases, optimised by stochastic gradient descent with bootstrap sampling of (user, positive item, negative item) triples; applied to matrix factorization and adaptive kNN and reported to outperform the standard learning techniques for those models on personalised ranking. — [Rendle et al., arXiv 1205.2618 (UAI 2009), primary abstract](https://arxiv.org/abs/1205.2618)

**EASE (Steck 2019) and SLIM**
- EASE is a linear item–item model with a single constraint — the diagonal of the weight matrix is zero — and a closed-form solution: P = (XᵀX + λI)⁻¹, B_ij = −P_ij / P_jj for i ≠ j, B_ii = 0. The only hyperparameter is the L2 weight λ (best values about 500 on ML-20M, 1,000 on Netflix, 200 on MSD). — [Steck, "Embarrassingly Shallow Autoencoders for Sparse Data", WWW 2019, primary](https://ar5iv.labs.arxiv.org/html/1905.03375)
- Cost: one inversion of the item × item Gram matrix, O(|I|³), independent of the number of users and interactions; the dense matrix must fit in memory. Reported training: under 2 minutes on Netflix (17,769 items), under 20 minutes on MSD (41,140 items) on a 64 GB / 16 vCPU machine. — [Steck 2019](https://ar5iv.labs.arxiv.org/html/1905.03375)
- Accuracy: EASE beat SLIM on all datasets (Recall@20 0.391 vs. 0.370 on ML-20M; 0.362 vs. 0.347 on Netflix) and beat the deep Mult-VAE on Netflix (0.362 vs. 0.351) and MSD (0.333 vs. 0.266), losing only slightly on ML-20M (0.391 vs. 0.395). A parallelised SLIM grid search was cited at about two weeks on Netflix and did not finish on MSD. — [Steck 2019](https://ar5iv.labs.arxiv.org/html/1905.03375)
- About 60% of EASE's learned weights are negative, and clipping them to zero lowers accuracy (ML-20M Recall@20 0.391 → 0.373) — i.e. it learns dissimilarity, which co-occurrence scores cannot. — [Steck 2019](https://ar5iv.labs.arxiv.org/html/1905.03375)
- RecTools' EASE implementation defaults to regularisation 500 and its docstring warns that `fit` needs a lot of RAM and that a reasonable catalog size for local development is about 30k items. — [RecTools EASE source, search summary](https://rectools.readthedocs.io/en/latest/_modules/rectools/models/ease.html)

**Reproducibility studies**
- RecSys 2019: of 18 neural top-n recommendation algorithms from top conferences, only 7 could be reproduced with reasonable effort; 6 of those 7 were often outperformed by simple heuristic methods (nearest-neighbour or graph-based); the remaining one did not consistently beat a well-tuned non-neural linear ranking method. — [Ferrari Dacrema, Cremonesi, Jannach, "Are We Really Making Much Progress?", arXiv 1907.06902, primary abstract](https://arxiv.org/abs/1907.06902)
- Extended TOIS version (works from 2015–2018): "11 out of the 12 reproducible neural approaches can be outperformed by conceptually simple methods". Baselines: TopPopular, UserKNN, ItemKNN, P3α, RP3β, content/hybrid KNN, iALS, PureSVD, SLIM (ElasticNet), EASE. No single baseline family won in every configuration. — [Ferrari Dacrema et al., arXiv 1911.07698, primary](https://ar5iv.labs.arxiv.org/html/1911.07698)
- Sparse-data specifics from the same study: on the Epinions dataset the non-personalised most-popular list beat every personalised technique; on another skewed dataset recommending the most popular items to everyone was by far the most effective; the one neural method (CDL) that beat the baselines did so only on a small, very sparse dataset with one training interaction per user (a setting where it could use item content). — [Ferrari Dacrema et al., arXiv 1911.07698](https://ar5iv.labs.arxiv.org/html/1911.07698)
- The authors attribute the "phantom progress" mostly to the choice and poor tuning of baselines. — [Ferrari Dacrema et al., arXiv 1911.07698, search summary](https://arxiv.org/pdf/1911.07698)
- iALS revisited (Rendle, Krichene, Zhang, Koren; RecSys 2022): on four benchmarks where iALS had been reported as weak, properly tuned iALS is highly competitive and best on at least half of the comparisons; the paper lists tuning practices. — [arXiv 2110.14037, search summary](https://www.arxiv.org/pdf/2110.14037)
- Practitioner data point: an item-pair matrix-factorization baseline on Amazon product-pair data (electronics: about 418k products, about 4M pairs, "99.99% empty") reached ROC-AUC 0.81 with binary labels and about 0.92 with weighted pair labels; training took about 45 minutes for 5 epochs on electronics and about 22 hours on books. — [Eugene Yan, "Beating the Baseline Recommender with Graph & NLP in Pytorch" (older practitioner write-up)](https://eugeneyan.com/writing/recommender-systems-baseline-pytorch/)

### Inferences
- Reading the three families against this store's data: (a) item-KNN / co-occurrence needs no training and degrades gracefully; (b) ALS/BPR learn a user vector, which for a customer with 1–3 purchases is barely determined — the model then mostly reproduces popularity plus item–item structure, at the price of hyperparameter tuning (factors, regularisation, α) and an offline evaluation harness the team does not have yet; (c) EASE is attractive because it has one hyperparameter and no iterations, but a dense 30,000 × 30,000 float64 matrix is about 7.2 GB (float32 about 3.6 GB) and the inversion is O(n³) — feasible on a 16–32 GB machine as a nightly job, impractical on a small app server; restricting it to items with at least a handful of purchases shrinks it drastically.
- The reproducibility literature evaluates on dense public datasets (MovieLens, Netflix, MSD). Its transferable lesson is methodological — tune and compare against TopPopular and item-KNN first — rather than a guarantee that EASE/iALS will beat co-occurrence on a store where most items have a handful of sales.
- Logistic MF and SLIM are not worth separate effort here: EASE supersedes SLIM in accuracy and training time per Steck; logistic MF is available in `implicit` but no evidence was found that it outperforms ALS/BPR.

### Gaps
- Logistic matrix factorization (Johnson 2014) was not sourced beyond its presence in the `implicit` library.
- The SLIM paper (Ning & Karypis 2011) was not read directly; SLIM facts above come via Steck 2019 and Ferrari Dacrema et al.
- No reproducibility study on a *small B2C/B2B retail* dataset with 1–3 orders per customer was found; all cited benchmarks are denser media/rating datasets.
- Later follow-ups (2022–2025 replication papers beyond the iALS revisit) were not surveyed in this session.

---

## 4. Behaviour on sparse data (most customers have 1–3 orders); minimum volumes; standard fallbacks

### Takeaway
There is no universal threshold, but the citable numbers converge on "about 10 purchase events per item on average and at least ~1,000 purchases" for a co-purchase model and "50,000 interactions from 1,000+ users with 2+ interactions" for a personalised model to be good; below that, item-based co-occurrence with count floors plus popularity and category-level back-off is the standard design. Item-based methods tolerate short customer histories; user-factor models do not.

### Cited Findings
- Amazon Personalize hard minimum for any model: 1,000 item interactions and 25 unique users with at least two interactions each; **recommended for quality**: at least 50,000 interactions from at least 1,000 users with two or more interactions each. "Best sellers" needs at least 1,000 purchase events. — [AWS Personalize docs, primary](https://docs.aws.amazon.com/personalize/latest/dg/interactions-datasets.html)
- Google Vertex AI Search for commerce: "Frequently Bought Together" — 1,000 purchase events, average 10 per catalog item in a 1-year window (or 90 days of purchase data within the last year), 100 unique purchased items. "Others You May Like" / "Recommended for You" — 10,000 detail-page-view (and, for conversion objectives, 10,000 add-to-cart) events in the last 90 days, average 10 per item, 100 unique items. "Buy it Again" — 1,000 purchase events, average 10 per item in 90 days. "Similar Items" — no user events at all, only catalog data (100 SKUs). — [Google docs, create-models, primary](https://docs.cloud.google.com/retail/docs/create-models)
- Google additionally asks for at least 100 unique visitor IDs per ingested event type. — [Google docs, user events](https://docs.cloud.google.com/retail/docs/user-events)
- Item-to-item CF was explicitly designed for new customers with only a few purchases and works from two or three items. — [Linden et al. 2003](https://www.cs.umd.edu/~samir/498/Amazon-Recommendations.pdf)
- On small / very sparse / skewed datasets a non-personalised most-popular list was the best method in more than one experiment of the TOIS reproducibility study. — [Ferrari Dacrema et al., arXiv 1911.07698](https://ar5iv.labs.arxiv.org/html/1911.07698)
- Hu et al. also call popularity ranking a surprisingly powerful baseline. — [Hu et al. 2008](http://yifanhu.net/PUB/cf.pdf)
- LightFM's paper claims that with user and item metadata it outperforms both pure collaborative and pure content-based models in cold-start or sparse-interaction scenarios, and is at least as good as pure MF when data is abundant. — [Kula 2015, arXiv 1507.08439, primary abstract](https://arxiv.org/abs/1507.08439)
- Shrinkage (a shrink term added to the similarity denominator) and neighbourhood size are the standard knobs that keep item-KNN from trusting pairs with tiny support. — [Ferrari Dacrema et al., arXiv 1911.07698](https://ar5iv.labs.arxiv.org/html/1911.07698)
- Fallback building blocks that ship in a maintained library: RecTools includes `PopularModel` and `PopularInCategoryModel` next to its CF models. — [RecTools on PyPI](https://pypi.org/pypi/rectools/json)
- Fresh-item heuristic from Google's course: approximate a new item's embedding by averaging the embeddings of items in the same category. — [Google ML recommendation course](https://developers.google.com/machine-learning/recommendation/collaborative/summary)
- Minimum support filters are "silent" exactly where new products, small segments and emerging behaviours are — the technique is reliable only where there is volume. — [Koji, vendor blog](https://www.koji.so/blog/market-basket-analysis-guide-2026)

### Inferences
- Applying Google's "10 purchases per item on average" rule to this store: a 30,000-SKU catalog would need about 300,000 purchased line items per year to meet it catalog-wide. A modest-volume store will meet it only for the head of the catalog; most SKUs will have too few orders for product-level co-occurrence. This is the central constraint and it argues for a **back-off ladder**, not for a more sophisticated model:
  1. product-level co-purchase pairs (pair count ≥ floor, normalised score);
  2. item-category-level co-purchase ("buyers of products in item category A also buy from item category B") → show the bestsellers / in-stock top products of B; aggregating to `ProductItemCategory` → `ProductSubCategory` multiplies the evidence per cell by orders of magnitude;
  3. content similarity (same item category, brand, attributes — section 5);
  4. popularity within the category, then global bestsellers / trending.
  Fill each widget top-down until it has N items.
- Practical floors (my judgement, not sourced): require each recommended pair to be supported by at least 3–5 distinct orders (or customers), require an anchor item to have at least ~10–20 orders before trusting its product-level list, and use a long window (12–24 months) because building-materials purchases are infrequent; shrinkage (adding a constant to the denominator) is a softer alternative to hard floors.
- Realism at this scale (synthesis of all sections):

| Method | Data needed | Useful from roughly | Compute / infra | Fit for this store |
|---|---|---|---|---|
| Popularity / trending (global, per category) | order lines | day one | one SQL GROUP BY | must-have fallback |
| Pairwise co-purchase (FBT), cosine/Jaccard/LLR | order baskets | ~1,000 orders; ~10 orders per anchor item | SQL self-join or sparse matrix product, nightly cron | core method |
| Category-level co-purchase back-off | order baskets + category tree | few hundred orders | SQL | core method for the long tail |
| Item-to-item CF over customer histories (+views/carts) | customer × item events | same as above; benefits from view data | same batch job | core method for "also bought/viewed" and personal blocks |
| Association rules (Apriori / FP-Growth, multi-item antecedents) | baskets, one-hot | dense baskets, small catalog | memory-heavy on wide catalogs | overkill; pairs suffice |
| Content-based (category/brand/attributes/text) | catalog only | zero interactions | TF-IDF + cosine, or SQL | needed for cold start |
| Implicit ALS / BPR | user × item matrix | ~50k interactions, 1,000+ users with 2+ (AWS guidance) | `implicit`, minutes on CPU; needs tuning + offline eval | optional later; weak with 1–3 orders per user |
| EASE | user × item matrix | similar; items with enough purchases | dense n×n inversion, GBs of RAM at 30k items | optional later, on the head of the catalog |
| LightFM hybrid | interactions + item/user features | sparse data with good metadata | CPU; original package stale, use the fork | optional; only if cold start dominates |
| User-based CF | dense user histories | not at 1–3 orders per user | — | not suitable |

### Gaps
- No peer-reviewed or engineering-blog source giving a minimum "orders per item" for trustworthy co-purchase pairs was found; the numeric floors above are either managed-service minimums (Google, AWS) or my own judgement.
- No source specific to building-materials / DIY retail (project-based baskets, contractor buyers) was found in this session.
- The category back-off ladder is common practice but is documented here only indirectly (RecTools `PopularInCategoryModel`, Google's category-average heuristic); no primary source describing a retailer's full fallback chain was found.

---

## 5. Cold start: new products, new / anonymous customers; content-based filtering, hybrids, popularity fallbacks

### Takeaway
Collaborative methods cannot say anything about a product with no orders or a visitor with no history; the standard answers are catalog-only "similar items" (category, brand, attributes, text), session-based item-to-item for anonymous visitors (use the product being viewed / the cart as the "history"), and popularity. A hybrid model such as LightFM formalises this but is only worth it when cold start is the dominant case.

### Cited Findings
- Collaborative filtering's stated weakness: an item not seen in training has no embedding; mitigations are projecting the new item from a few interactions without retraining (WALS) or heuristics such as averaging the embeddings of same-category items; side features are not easy to include in plain WALS. Its strengths: no domain knowledge needed, serendipity, only the feedback matrix required. — [Google ML recommendation course](https://developers.google.com/machine-learning/recommendation/collaborative/summary)
- Hu et al. frame the trade-off the same way: CF is generally more accurate than content-based techniques but cannot address products new to the system, for which content-based approaches are adequate. — [Hu et al. 2008](http://yifanhu.net/PUB/cf.pdf)
- Google's managed "Similar Items" model needs no user events — only the product catalog; Google notes its text-based features work best with at least 10 description words per product on average. — [Google docs, models](https://docs.cloud.google.com/retail/docs/models); [Google docs, create-models](https://docs.cloud.google.com/retail/docs/create-models)
- LightFM: a hybrid matrix factorization in which each user and item is the sum of the latent vectors of its features (e.g. category, brand, attribute values), so a brand-new product gets a representation from its metadata; trained with BPR or WARP ranking losses; claimed to beat both collaborative and content-based models in cold-start / sparse scenarios and to match pure MF when interactions are abundant. — [Kula 2015, arXiv 1507.08439](https://arxiv.org/abs/1507.08439); [LightFM GitHub](https://github.com/lyst/lightfm)
- The TOIS reproducibility study includes content-based and hybrid KNN baselines (ItemKNN-CBF, ItemKNN-CFCBF: item similarity from features, or from features concatenated with interactions) among the simple methods that are competitive. — [Ferrari Dacrema et al., arXiv 1911.07698](https://ar5iv.labs.arxiv.org/html/1911.07698)
- Amazon's item-to-item method works for a customer with two or three items, and Amazon's cart recommendations are computed from the items currently in the shopping cart — i.e. the "user profile" can be the current session. — [Linden et al. 2003](https://www.cs.umd.edu/~samir/498/Amazon-Recommendations.pdf)
- New users in a managed service: AWS notes that contextual metadata (e.g. device) can make recommendations more relevant for users with no history, and its e-commerce domain ships "Best sellers" and "Most viewed" popularity recommenders. — [AWS Personalize docs](https://docs.aws.amazon.com/personalize/latest/dg/interactions-datasets.html)

### Inferences
- New product: serve a content-based "similar products" list — same `ProductItemCategory`, then shared brand, overlap of attribute values (`ProductAttributeValue`: list/boolean values as tokens, numeric values bucketed), TF-IDF/BM25 over the product name — and let the new product *inherit* the co-purchase list of its nearest established neighbours or of its item category until it has orders of its own. The store already has a rich structured attribute model, which is usually a stronger similarity signal than free text for building materials (dimensions, material, compatibility).
- Content similarity yields *substitutes* (similar drills), not *complements* (drill + bits). For a new product's "bought together" slot, the category-level co-purchase table is the right fallback, not content similarity.
- Anonymous / new customer: (a) on a product page, item-to-item needs no user at all; (b) on the cart page, use cart contents as the history (the store keeps carts and favourites by cookie token, and recently viewed products); (c) on the home page, popularity / trending, optionally per category of the last viewed products.
- TF-IDF / BM25 with scikit-learn (`TfidfVectorizer` + cosine / `NearestNeighbors`) or PostgreSQL trigram / full-text similarity is sufficient at tens of thousands of products; this is background knowledge, not verified against docs in this session. Product names in three languages (uz/ru/en) mean text features should be computed on one canonical language.
- LightFM is justified only if offline evaluation shows the simple "content fallback + co-occurrence" combination is clearly inadequate; it brings a training pipeline, hyperparameters and a package with maintenance risk (section 7).

### Gaps
- No source quantifying how much content-based similarity recovers of CF quality on retail cold-start items was found.
- BM25 libraries for content similarity (e.g. `rank_bm25`) and scikit-learn specifics were not checked in this session.
- Trending / time-windowed popularity formulas (e.g. decayed counts) were not sourced beyond SAR's half-life decay (section 6).

---

## 6. Combining purchases with weaker implicit signals (cart adds, favourites, views); weighting and time decay

### Takeaway
The common pattern is a per-event weight with purchase > add-to-cart > favourite/click > view, summed per (user, item), multiplied by an exponential time decay, and then fed to the same co-occurrence / ALS machinery; the concrete numbers in circulation are heuristics, not derived constants, and should be tuned on held-out orders. Keeping purchases as the "primary" signal and using views/carts as secondary evidence is the safe design.

### Cited Findings
- Microsoft SAR's user–item affinity: a_ij = Σ_k w_k · (1/2)^((t0 − t_k)/T), summed over all events k of user i on item j, where w_k is the weight of the event type and T is the half-life (an event T units before t0 counts half); the deep-dive notebook uses T = 30 days; setting all weights to 1 ignores event types and T = ∞ ignores time. Recommendation scores are affinity matrix × item-similarity matrix, optionally removing already-seen items. — [Microsoft Recommenders, SAR deep dive, primary](https://raw.githubusercontent.com/recommenders-team/recommenders/main/examples/02_model_collaborative_filtering/sar_deep_dive.ipynb)
- SAR caveats stated in the notebook: O(n³) complexity for the algorithm and a single-node implementation not meant for large datasets; scores are for ranking only, not on a rating scale. — [SAR deep dive](https://raw.githubusercontent.com/recommenders-team/recommenders/main/examples/02_model_collaborative_filtering/sar_deep_dive.ipynb)
- Hu/Koren/Volinsky: the event magnitude should raise **confidence**, not preference — c_ui = 1 + α·r_ui (α = 40) or the log form; a one-off event may be noise, a recurring event more likely reflects real preference. — [Hu et al. 2008](http://yifanhu.net/PUB/cf.pdf)
- Eugene Yan's pair weights when merging relationship types into one score: bought-together 1.2, also-bought 1.0, also-viewed 0.5, summed per product pair (the weighted labels trained far better than binary ones: AUC about 0.92 vs. 0.81). — [Eugene Yan (older practitioner write-up)](https://eugeneyan.com/writing/recommender-systems-baseline-pytorch/)
- A vendor's default reward map: purchase 3.0, add-to-cart 2.0, click 1.0, view 0.0, with an e-commerce example raising purchase to 5.0; decay is expressed as a multiplicative factor (0.995 or 0.990) and events older than a window are dropped. — [Mixpeek docs, vendor, search summary](https://mixpeek.com/docs/retrieval/reward-signals)
- Managed services encode the same idea: AWS Personalize lets newer recipes assign different weights per event type (e.g. purchase above click), otherwise all events count equally; it uses timestamps to compute recency. — [AWS Personalize docs](https://docs.aws.amazon.com/personalize/latest/dg/interactions-datasets.html)
- Google's models pick different event types per objective: FBT uses purchase events; "Others You May Like" uses detail-page views (plus add-to-cart for conversion objectives) — i.e. views are the main signal for substitutes, purchases for complements. — [Google docs, create-models](https://docs.cloud.google.com/retail/docs/create-models)
- Time decay is not uniformly beneficial: a study on the Retailrocket e-commerce dataset reports decay improving MF and SLIM variants but *reducing* accuracy for a KNN variant. — [search summary of a Springer / J. Supercomputing 2022 article; not opened](https://link.springer.com/article/10.1007/s11227-022-04580-7)
- Heavy-user damping: BM25 weighting of the interaction matrix (K1 = 100, B = 0.8 in the `implicit` tutorial) reduces the impact of users with very many interactions and of popular items. — [implicit tutorial](https://benfred.github.io/implicit/tutorial_lastfm.html)

### Inferences
- A defensible starting scheme for this store (to be tuned, not sourced as-is): purchase 1.0 (per order, not per unit quantity — quantity in building materials reflects project size, not preference; use log(1+qty) at most), add-to-cart ≈ 0.5, favourite ≈ 0.3–0.5, product view ≈ 0.1–0.2 with a cap per user–item; half-life 90–180 days for purchases (slow purchase cycle) and 14–30 days for views. The cited sources agree on the ordering but disagree on magnitudes (1.2/1.0/0.5 vs. 3/2/1/0).
- Two ways to combine: (a) one weighted user × item matrix for a single similarity table (simple, what SAR does); (b) separate tables per signal — purchase-based FBT (complements) and view-based "others also viewed" (substitutes) — blended or shown in different widgets. With sparse orders, view/cart co-occurrence is typically the only way to get coverage on long-tail products, but it changes the semantics towards substitutes, so (b) is safer.
- Signals available in this codebase: `OrderItem` (purchases, by customer), `CartItem` and `Favourites` (customer or cookie token), `RecentlyViewedProducts`. Only completed / non-cancelled orders should count as purchases; cancelled and refunded orders are a candidate negative or at least excluded signal.
- Time decay belongs in the *user affinity* (what the customer did recently) more than in the *item–item* table; decaying the item table shortens the already thin evidence. A long window with mild or no decay for item similarity, plus recency weighting at serving time, fits sparse data better.

### Gaps
- No primary, quantitative source establishing "correct" relative weights of purchase / cart / favourite / view was found; all numbers are heuristics from a practitioner blog and a vendor.
- The Retailrocket time-decay study was not opened; the attribution to the linked Springer article is from the search summary and should be re-verified before quoting.
- Mahout-style cross-occurrence (using views as secondary indicators for purchases with LLR) could not be verified from primary docs in this session.

---

## 7. Open-source libraries and their status in 2025–2026

### Takeaway
As of October 2026 the practical shortlist for plain Python without ML infrastructure is: `implicit` (item-KNN, ALS, BPR; MIT), `RecTools` (one API over implicit / EASE / popular / LightFM plus metrics and splitters; Apache-2.0, released June 2026) and `mlxtend` (association rules; BSD, released June 2026). Original `LightFM` has had no release since March 2023 (use the `rectools-lightfm` fork), `Surprise` is explicit-ratings only, `RecBole` is a PyTorch research framework — both are a poor fit here.

### Cited Findings

| Library | What it gives | Licence | Latest release (as checked 2026-10-10) | Notes |
|---|---|---|---|---|
| `implicit` | ALS, BPR, logistic MF, item-item KNN (cosine / TF-IDF / BM25) on scipy sparse matrices; `recommend`, `similar_items`, `filter_already_liked_items` | MIT | 0.7.3; requires Python ≥ 3.9, tested on 3.9–3.14 on Linux/macOS/Windows; optional CUDA | 3.8k stars, 90 open issues; release date of 0.7.3 not retrieved — [GitHub](https://github.com/benfred/implicit); [PyPI](https://pypi.org/pypi/implicit/json); [tutorial](https://benfred.github.io/implicit/tutorial_lastfm.html) |
| `LightFM` (lyst) | hybrid MF with user/item features; BPR and WARP losses | Apache-2.0 per GitHub (PyPI metadata says MIT — conflicting) | 1.17, uploaded 2023-03-20; previous 1.16 in Nov 2020 | 5.1k stars, 151 open issues, effectively unmaintained — [GitHub](https://github.com/lyst/lightfm); [PyPI](https://pypi.org/pypi/lightfm/json) |
| `rectools-lightfm` | fork of LightFM kept installable on new Python versions; maintainers state they will fix compatibility but not extend functionality | — | 1.17.x | [PyPI, search summary](https://pypi.org/project/rectools-lightfm/1.17.1) |
| `RecTools` (MTS) | unified dataset / model / metrics API; `PopularModel`, `PopularInCategoryModel`, `EASEModel`, `PureSVDModel`, wrappers `ImplicitALSWrapperModel`, `ImplicitBPRWrapperModel`, `ImplicitItemKNNWrapperModel`, `LightFMWrapperModel`; neural models (SASRec, BERT4Rec, DSSM, HSTU) behind an optional `torch` extra | Apache-2.0 | 0.19.0, uploaded 2026-06-13; Python ≥ 3.9, < 3.14 | actively developed — [PyPI](https://pypi.org/pypi/rectools/json); [docs](https://rectools.readthedocs.io/) |
| `mlxtend` | `apriori`, `fpgrowth`, `fpmax`, `association_rules` (support, confidence, lift, leverage, conviction, Zhang, Jaccard, certainty, Kulczynski) on one-hot pandas DataFrames | BSD 3-Clause | 0.25.0, uploaded 2026-06-06; Python ≥ 3.11 | maintained — [PyPI](https://pypi.org/pypi/mlxtend/json); [docs](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/) |
| `Surprise` (`scikit-surprise`) | SVD / KNN for **explicit ratings**; its own description says it does not support implicit ratings or content-based information | BSD 3-Clause | 1.1.5, uploaded 2026-05-30; Python ≥ 3.10 | not applicable to purchase-history data — [PyPI](https://pypi.org/pypi/scikit-surprise/json) |
| `RecBole` | research framework with a very large model zoo; depends on `torch>=1.10.0` | MIT (classifier) | 1.2.1, uploaded 2025-02-24 | heavy for a no-ML-infra team — [PyPI](https://pypi.org/pypi/recbole/json) |
| `Cornac` | comparative framework, many models incl. multimodal | Apache-2.0 | 3.0.1; Python ≥ 3.10 (release date not retrieved) | [PyPI](https://pypi.org/pypi/cornac/json) |
| `LensKit` | research/teaching toolkit for experiments | not verified | 2026.2.1 per PyPI stats | appears active — [PyPI stats, search summary](https://pypistats.org/packages/lenskit) |
| Microsoft `recommenders` | reference implementations and notebooks, incl. SAR (co-occurrence + Jaccard/lift + time decay) | not verified | not checked | useful as a reference for SAR — [SAR notebook](https://raw.githubusercontent.com/recommenders-team/recommenders/main/examples/02_model_collaborative_filtering/sar_deep_dive.ipynb) |

- `implicit` expects (user, item) scipy CSR matrices; ALS example parameters in its tutorial: `factors=64, regularization=0.05, alpha=2.0`. — [implicit tutorial](https://benfred.github.io/implicit/tutorial_lastfm.html)
- A Snyk snapshot rated `scikit-surprise` maintenance as inactive after its May 2024 release (1.1.4); PyPI now shows 1.1.5 from May 2026, so it still receives compatibility releases. — [Snyk, search summary](https://snyk.io/advisor/python/scikit-surprise); [PyPI](https://pypi.org/pypi/scikit-surprise/json)

### Inferences
- Minimal-dependency path for this project: the co-purchase / item-to-item tables need **no recommender library at all** — PostgreSQL (self-join on order items) or numpy/scipy (`X.T @ X` on a sparse order × product matrix) inside a Django management command run by cron, results in a table and/or Redis. This matches the project's existing pattern (`recalculate_badges`, `import_characteristics` as cron commands).
- If a library is wanted: `implicit` alone covers item-KNN with BM25/TF-IDF weighting and ALS/BPR with a tiny API and prebuilt wheels (including Windows, relevant for the dev machine); `RecTools` is the choice if the team wants ready-made offline evaluation (time-based splits, ranking metrics) and to compare popular / item-KNN / ALS / EASE under one interface — the evaluation harness is arguably more valuable than any model.
- `mlxtend` is fine for exploratory basket analysis in a notebook but its one-hot DataFrame input is a poor production fit for tens of thousands of SKUs.
- scikit-learn has no recommender module but supplies the content-based pieces (`TfidfVectorizer`, `cosine_similarity`, `NearestNeighbors`, `TruncatedSVD`); background knowledge, not verified in this session.
- Licences of everything on the shortlist (MIT, BSD-3, Apache-2.0) are permissive and unproblematic for a commercial backend.

### Gaps
- Release dates for `implicit` 0.7.3 and `cornac` 3.0.1 were not retrieved (PyPI JSON truncated); last-commit dates were not checked for any repository.
- LightFM's licence is reported inconsistently (GitHub: Apache-2.0; PyPI metadata: MIT) — check the repository's LICENSE file before relying on it.
- LensKit's and Microsoft Recommenders' licences and current release status were not verified from primary pages.
- scikit-learn was not checked against its documentation in this session.
