# Purchase-history recommendations in building materials / DIY / home improvement (state of practice, Oct 2026)

Source-type tags used below:
- **[P]** peer-reviewed or first-party research paper (read in full or abstract/full text fetched)
- **[F]** first-party company statement (press release, corporate page) — factual about features, not about effect sizes
- **[UX]** independent UX research (Baymard)
- **[T]** trade press / third-party description
- **[V]** vendor or agency marketing — treat numbers as unverified
- **(snippet)** = the fact was retrieved only as a search-result excerpt; the page itself could not be fetched (403 / timeout / anti-bot), so wording may be imprecise

Age: sources from 2015–2020 are marked "(old)"; they are still the canonical references, nothing newer has replaced them.

---

## 1. Complementary vs. substitute products

### Takeaway
"Also bought" data mixes complements, substitutes and coincidental co-purchases; the published fix is the same everywhere: treat view-based links as substitutes, purchase-based links as complements, subtract the former from the latter, and predict complements at the category/product-type level first, then pick one good item per complementary category. Complement links are directional (drill -> drill bits, not drill bits -> drill).

### Cited Findings
- **Definitions.** Substitutes are products that can be purchased instead of each other; complements are products purchased in addition to each other. [P, old — McAuley, Pandey, Leskovec, KDD 2015, "Sceptre"] — [arXiv 1506.08839](https://ar5iv.arxiv.org/html/1506.08839)
- **Which behavioural signal maps to which relation (Sceptre's ground truth on Amazon):** "users who viewed X also viewed Y" (91M edges) and "users who viewed X eventually bought Y" (8.18M edges) = **substitutes**; "users who bought X also bought Y" (133M edges) and "frequently bought X and Y together" (4.6M edges, same basket) = **complements**. [P, old] — [arXiv 1506.08839](https://ar5iv.arxiv.org/html/1506.08839)
- **Why the distinction matters for timing:** a user who is buying a phone should be shown batteries, cases or chargers; the paper states that "recommending a laptop to a user already purchasing a battery makes little sense". (The paper does not use a drill example; the drill case is the same failure in this domain.) [P, old] — [arXiv 1506.08839](https://ar5iv.arxiv.org/html/1506.08839)
- **Links are directional.** Sceptre first predicts whether two products are related, then the direction; a battery may complement a laptop without the reverse; substitution can also be one-way (a cheaper, better-rated product substitutes a pricier one, not vice versa). [P, old] — [arXiv 1506.08839](https://ar5iv.arxiv.org/html/1506.08839)
- **Category hierarchy is central in Sceptre:** each topic is tied to a node of the category tree and a product only uses topics on its own category path (about 10–20 active per product). Reported accuracy: 94.83% average for substitute links, 90.23% for complement links; 91.28–93.67% in cold start using descriptions only. These are balanced link-prediction accuracies on Amazon's own link data, not online results. [P, old] — [arXiv 1506.08839](https://ar5iv.arxiv.org/html/1506.08839)
- **Co-purchase is a noisy label.** The 2024 survey of 34 complementary-recommendation studies (2009–2024) states "co-purchased products are not necessarily complementary" (its example: bananas and bottled water) and that buy-together "may not necessarily complement". [P — survey] — [arXiv 2403.16135](https://ar5iv.labs.arxiv.org/html/2403.16135)
- **Standard cleaning step:** some works treat pairs that are also co-viewed as substitution relations "and remove them from the set of complementary relations"; the survey lists "buy together + view together" as the signal combination used by P-Companion and one other study. "Use together" would be the more realistic label, but "there is no ready dataset". [P — survey] — [arXiv 2403.16135](https://ar5iv.labs.arxiv.org/html/2403.16135)
- **Asymmetry again:** "there may be asymmetry in the complementary relationship" — a phone suggests a charger, a charger should not suggest a phone. [P — survey] — [arXiv 2403.16135](https://ar5iv.labs.arxiv.org/html/2403.16135)
- **P-Companion (Amazon, CIKM 2020, old):** argues co-purchased products are not always complementary and proposes cleaner distant-supervision labels; given a product and its product type, an encoder-decoder first predicts **several complementary product types**, then a second network finds the best product inside each predicted type; handles cold-start products through a pretrained product embedding (Product2vec); reported +7.1% over baselines offline. Explicit goal: relevance **and diversity across categories**. [P] — [Amazon Science](https://amazon.science/publications/p-companion-a-principled-framework-for-diversified-complementary-product-recommendation); method summary also in [arXiv 2403.16135](https://ar5iv.labs.arxiv.org/html/2403.16135)
- **Category-level complement modelling is common, also for cold start:** the survey notes methods that learn complementary relationships between categories as well as products, and methods that use category vectors as stand-ins for new products because "when products are related, the categories to which the products belong are also relevant". [P — survey] — [arXiv 2403.16135](https://ar5iv.labs.arxiv.org/html/2403.16135)
- **Basket-based embedding (triple2vec):** models (item, item, user) triples from shopping baskets; paper title "Representing and Recommending Shopping Baskets with Complementarity, Compatibility and Loyalty", CIKM 2018 (old), first author Mengting Wan (UC San Diego). [P] — [arXiv 2403.16135](https://ar5iv.labs.arxiv.org/html/2403.16135); bibliographic record: [OpenAlex](https://api.openalex.org/works/doi:10.1145%2F3269206.3271786)
- **Home Depot uses category-level association analysis:** a 2020 interview with a Home Depot data-science leader says the team used statistical analysis and association rules to discover relationships between different categories (old; snippet — Forbes returned 403). [T] — [Forbes, 17 Oct 2020](https://www.forbes.com/sites/cognitiveworld/2020/10/17/how-home-depot-is-enhancing-the-ecommerce-experience-with-ai/)
- **Home Depot accessory patent:** describes an "Item Related Groups" database of manually entered anchor–accessory relationships between SKUs, and the rule that only one accessory SKU from a given accessory product category may be recommended for an anchor product (snippet — the patent page reset the connection). [F — patent application US 2020/0104898, Home Depot Product Authority, LLC] — [FreePatentsOnline](https://www.freepatentsonline.com/y2020/0104898.html)
- **UX evidence that substitutes are the wrong thing late in the funnel:** Baymard advises to limit alternative products in the cart, because shoppers ready to check out may leave to pursue an alternative and not return; supplementary items should be prioritised (exception: upgrades / newer versions of the same product). [UX, 2021] — [Baymard](https://baymard.com/research-articles/product-recommendations-cart)

### Inferences
- A workable rule set without any ML, consistent with the papers above: (1) same leaf category as the purchased/viewed item = substitute candidate, show only before purchase ("similar products"); (2) different leaf category + co-purchase support = complement candidate; (3) drop complement candidates that are also strongly co-viewed with the anchor; (4) aggregate co-purchases to a category -> category matrix and keep only pairs whose target category is a plausible accessory/consumable for the source category; (5) emit at most one item per target category. Step 4–5 is exactly the "predict complementary types, then one item per type" structure of P-Companion and the "one accessory per accessory category" rule in Home Depot's patent.
- Direction must be stored: compute P(Y in basket | X in basket) rather than a symmetric score, and/or keep the rule "cheap consumable does not recommend the expensive durable".
- In building materials the "bananas and water" noise is large: a foreman's order contains many unrelated bestsellers (cement, drywall, screws, bags), so raw co-occurrence will surface popular items; a lift / PMI style normalisation and the category whitelist matter more than model sophistication. (Inference from the survey's noise discussion; no home-improvement paper quantifies this.)

### Gaps
- No Instacart or Wayfair first-party publication on complementary-item recommendation was retrieved in this session; whether triple2vec used Walmart/Instacart data could not be confirmed from the retrieved record (the paper is commonly associated with Instacart/Dunnhumby baskets — unverified here).
- P-Companion's online A/B numbers and its exact label formula were not retrieved (only the abstract and the survey's description).
- Two US patents surfaced whose inventors overlap with Home Depot's RecSys-2019 authors (Al Jadda, Ahsan, Qu, Coombs): "Complementary item recommendations based on multi-modal embeddings" ([US12282946B2](https://patents.google.com/patent/US12282946)) and "Product recommendations based on items frequently bought together" ([US12131366B2](https://patents.google.com/patent/US12131366)). The assignee was not confirmed in the retrieved text, so the Home Depot attribution is probable, not verified; contents were not read.
- No published head-to-head (online) comparison of "simple category-mapping heuristic vs. learned complement model" for a DIY retailer was found.

---

## 2. Durable vs. consumable goods — what to re-recommend after purchase

### Takeaway
Retailers decide "repeat-purchasable or not" from data, per product or per category: the share of buyers who bought it more than once (Amazon's RCP with a threshold). Anything below the threshold is never shown in "buy again"; anything above it is shown, timed by the typical interval between purchases. No home-improvement retailer has published its own list or thresholds.

### Cited Findings
- **Amazon's gate:** Repeat Customer Probability, RCP = (# customers who bought the product more than once) / (# customers who bought it at least once); only products with RCP above a threshold are "deemed repeat purchasable", and every model in the paper (RCP, ATD, PG, MPG) applies this filter first. The threshold value is not disclosed. [P, old — Bhagat et al., KDD 2018] — [Amazon Science PDF](https://cdn.amazon.science/40/e5/89556a6341eaa3d7dacc074ff24d/buy-it-again-modeling-repeat-purchase-recommendations.pdf)
- **Repeat purchasing is not limited to obvious consumables:** the paper notes it is prevalent for consumables (toothpaste, diapers, cat food) but "present even in other categories like electronics, computers" (HDMI cables, memory cards). [P, old] — [Amazon Science PDF](https://cdn.amazon.science/40/e5/89556a6341eaa3d7dacc074ff24d/buy-it-again-modeling-repeat-purchase-recommendations.pdf)
- **Timing matters as much as eligibility:** a pure count ranking keeps showing items that are no longer timely; a plain time-decay score gives the highest score right after purchase, which the authors call counter-intuitive for consumables ("the need for a customer to repeat buy a product immediately after their purchase of the product is likely to go down"). [P, old] — [Amazon Science PDF](https://cdn.amazon.science/40/e5/89556a6341eaa3d7dacc074ff24d/buy-it-again-modeling-repeat-purchase-recommendations.pdf)
- **Category level may be the better grain:** Target's PCIC paper (RecSys 2023 short paper; "guests" = Target terminology, Target Tech blog of 1 Nov 2023 covers the same work) argues item-level analysis misses repeat behaviour, because on the retailer's data repeat *categories* per customer outnumber repeat *items*; it first predicts the categories a customer will repurchase, then ranks items within them. Reported: up to +16% NDCG and about +2% recall over 12 baselines on four public datasets, plus an unquantified "significant" A/B gain. [P] — [arXiv 2308.01195](https://arxiv.org/abs/2308.01195); [Target Tech blog](https://tech.target.com/blog/buy-it-again)
- **What pros re-buy in home improvement (descriptive, not a model):** Home Depot's Pro page lets pros "create product lists for your most-used items" (snippet) [F] — [Home Depot Pro Resource Center](https://www.homedepot.com/c/pro_resource_center); a contractor-software blog gives the typical examples: the same set of fasteners, specific paint colours, regular lumber dimensions (snippet) [T] — [ServiceTitan](https://www.servicetitan.com/blog/home-depot-pro-xtra)
- **Home Depot volume-pricing categories** named by third parties — drywall, insulation, conduit (snippet; thresholds differ between sources) — indicate which categories are bought repeatedly and in bulk. [T] — [ServiceTitan](https://www.servicetitan.com/blog/home-depot-pro-xtra)

### Inferences
- For a building-materials store the split is easiest at item-category level, computed from own orders: repeat rate per category = customers with >= 2 separate orders containing the category / customers with >= 1. Expected high-repeat groups: fasteners, drill bits / discs / blades, sandpaper and abrasives, paint, primer, sealants and foams, adhesives, dry mixes (cement, plaster, tile adhesive, grout), drywall and profiles, tape, rollers/brushes, gloves, bags. Expected near-zero: power tools, ladders, sanitary ware, doors, boilers, lighting fixtures. This list is domain common sense, **not** taken from a published source.
- Two different exclusion rules follow: (a) durable just bought -> exclude the item **and its substitutes (same leaf category)** from recommendations for a long window, but promote its complements (consumables/accessories); (b) consumable just bought -> eligible for "buy again", but suppressed for a short window after purchase (see section 3).
- Project materials (tiles, laminate, wallpaper) behave like durables for a B2C customer (one bathroom) but like consumables for a foreman (the next client's bathroom) — the same category needs a different rule per customer role, or a per-customer repeat signal instead of a category flag.
- With a small order base, a category-level RCP is far more stable than a SKU-level one (the same argument as PCIC's "more repeat categories than repeat items").

### Gaps
- No home-improvement retailer has published category repurchase rates, RCP thresholds or exclusion windows. Amazon does not publish its threshold.
- No source was found that documents how any retailer suppresses already-bought durables ("you just bought a drill, here is another drill"); the problem is widely discussed but the retrieved first-party sources only describe the positive side (what to recommend).

---

## 3. Repeat purchase / replenishment recommendation

### Takeaway
Repeat-item prediction is the easy part of next-basket recommendation and simple personal-frequency baselines are nearly unbeatable; the published gains come from adding a time-since-last-purchase term calibrated to the product's typical repurchase interval. With little data: personal frequency + recency, aggregated interval per product/category, and a "not too early" rule.

### Cited Findings
- **Amazon "Buy It Again" (KDD 2018, old), four models in increasing complexity:**
  - RCP — rank the customer's previously bought, repeat-purchasable products by the product's RCP; ignores time.
  - ATD (Aggregate Time Distribution) — per product, fit a log-normal distribution to the repeat-purchase intervals of all repeat buyers (log-normal fitted best for most consumables); rank by the density at the customer's current time since last purchase. Motivation: "for most customers we only have a few repeat purchases for a specific product", but many customers per product.
  - PG (Poisson-Gamma) — personal rate λ = (k + α) / (t + β): k = the customer's purchase count of the product, t = time since first purchase, α/β = product-level gamma prior fitted from all repeat buyers (empirical Bayes, so sparse customers fall back to the product average).
  - MPG (modified PG) — fixes PG's flaw that the estimated rate is highest right after a purchase: λ = (k + α) / (t_purch + 2·|t_mean − t| + β) while t < 2·t_mean, so the score rises until the customer's own mean interval and falls after it.
  [P] — [Amazon Science PDF](https://cdn.amazon.science/40/e5/89556a6341eaa3d7dacc074ff24d/buy-it-again-modeling-repeat-purchase-recommendations.pdf)
- **Offline lift at rank 3 vs. the RCP baseline:** ATD +8.22% precision / +5.56% recall / +5.70% nDCG; PG +32.34% / +29.04% / +37.11%; MPG +36.51% / +30.33% / +39.42%. I.e. the big step is using the customer's own purchase count and timing; the product-level interval alone adds little. [P] — [Amazon Science PDF](https://cdn.amazon.science/40/e5/89556a6341eaa3d7dacc074ff24d/buy-it-again-modeling-repeat-purchase-recommendations.pdf)
- **Online:** introducing Buy It Again (ATD model) on Amazon's personalized recommendations page vs. the existing recommendations: +7.1% CTR (p = 0.001); MPG vs. ATD: +1.3% CTR (p = 0.015); 14-day tests. RCP and PG were **not** tested online "due to the negative customer feedback we received from internal beta customers about these model recommending products too early". The metric is CTR on one page (purchases are said to be positively correlated but are not reported); the feature displaced another widget on that page. [P] — [Amazon Science PDF](https://cdn.amazon.science/40/e5/89556a6341eaa3d7dacc074ff24d/buy-it-again-modeling-repeat-purchase-recommendations.pdf)
- **In January 2014 the authors found no customer-facing repeat-purchase recommendation feature on popular e-commerce sites** — "buy again" as a widget is a post-2014 pattern. [P] — [Amazon Science PDF](https://cdn.amazon.science/40/e5/89556a6341eaa3d7dacc074ff24d/buy-it-again-modeling-repeat-purchase-recommendations.pdf)
- **"A Next Basket Recommendation Reality Check" (Li, Jullien, Ariannezhad, de Rijke; ACM TOIS 2023):** baselines G-TopFreq (globally most popular), P-TopFreq (the user's own most frequent items), GP-TopFreq (personal first, global to fill empty slots). Recall@10 on Instacart: GP-TopFreq 0.3269 vs. TIFU-KNN 0.3601, UP-CF@r 0.3506, DNNTSP 0.3330, Sets2Sets 0.2125, CLEA 0.1221, Dream 0.0712; on Dunnhumby: GP-TopFreq 0.2356 vs. UP-CF@r 0.2428, DNNTSP 0.2404, TIFU-KNN 0.2396; on TaFeng: GP-TopFreq 0.1211 vs. DNNTSP 0.1526, TIFU-KNN 0.1251. [P] — [arXiv 2109.14233](https://ar5iv.labs.arxiv.org/html/2109.14233)
- **Conclusions of the same paper:** no method wins consistently; improvements over GP-TopFreq are modest or absent; repeat items are much easier to predict than new ("explore") items; repeat recommendations account for over 97% of the overall performance of TIFU-KNN, UP-CF@r, Sets2Sets and DNNTSP on Dunnhumby and Instacart; repeat-biased methods can fall below global popularity for users with a low repeat ratio (0–0.2). UP-CF@r is the recency-aware user-based collaborative filtering method; TIFU-KNN is the personalized-item-frequency kNN method. [P] — [arXiv 2109.14233](https://ar5iv.labs.arxiv.org/html/2109.14233)
- **Dataset repeat ratios (share of next-basket items already bought before):** TaFeng 0.188, Dunnhumby 0.409, Instacart 0.597 — all grocery / household retail; none is a DIY dataset. [P] — [arXiv 2109.14233](https://ar5iv.labs.arxiv.org/html/2109.14233)
- **Target PCIC (2023):** survival models for general consumption rate + time-series features for trend, at category grain, then item ranking inside the category; trained on 100M customers / 3M items in a bit over 8 hours. [P] — [arXiv 2308.01195](https://arxiv.org/abs/2308.01195)
- **Lowe's lets the customer do the ranking:** its pro "Buy it Again" list can be sorted by frequency, recency and price of purchase (snippet). [T] — [Modern Distribution Management](https://www.mdm.com/news/technology/lowes-launches-digital-mvp-business-tools-for-pros/)

### Inferences
- What works with little data, in order of effort: (1) "Buy again" = the customer's own previously purchased SKUs from repeat-eligible categories, in stock, sorted by purchase count then recency (P-TopFreq); (2) hide an item for a fraction of its typical interval after the last purchase (the "too early" complaint is the one failure Amazon reports); (3) estimate the typical interval per **category** from all customers (ATD at category grain) and boost items whose time since last purchase is near it; (4) only then per-customer rates (PG/MPG). Steps 1–2 need no training.
- The Amazon and grocery intervals are consumption-driven (a household runs out). In building materials the trigger is job-driven: a foreman re-buys when the next job starts, so intervals are irregular and quantity-heavy. Frequency and "same SKU across several distinct orders" are probably more reliable than interval modelling for this customer group. This is an inference; no paper tests it on DIY data.
- Because repeat ratio differs by user group, one widget logic should not serve everyone: pros get a repeat-heavy list, one-off B2C renovators get complement/project recommendations (the reality-check paper's finding that repeat-biased methods underperform popularity for low-repeat users).
- Evaluate a "buy again" widget separately from discovery widgets; mixing them hides that almost all offline accuracy comes from repeats.

### Gaps
- No public next-basket / repeat-purchase benchmark exists for building materials or DIY; all numbers above are grocery, household or Amazon-wide.
- Instacart's own reorder models were not retrieved from a first-party source in this session.
- Target's blog post body could not be fetched (only title/date), so its practical lessons are not included.

---

## 4. Project-based shopping in home improvement

### Takeaway
Home improvement retailers treat "the project" (bathroom, flooring, painting) as the unit of demand and solve it mostly with curated or semi-curated structures — accessories, collections and parts linked to an anchor product, how-to content linked to products, calculators — rather than with a pure behavioural model. Since late 2025 the frontier is LLM agents that turn a project description into a grouped materials list (Home Depot). Russian/CIS DIY chains publish almost nothing technical on this.

### Cited Findings
- **Home Depot, RecSys 2019 industry talk "Recommendation in home improvement industry, challenges and opportunities" (old):** names Item Related Groups (IRG) as one of the most important recommendation types on home-improvement portals, in three kinds — **accessories** (a water filter for a fridge), **collections** (a faucet with shower head, towel bar and towel ring matching in style), **parts** (the handle of a drawer); challenges range from visual compatibility to understanding functionality; the approach combines computer vision, deep learning, NLP/NLU and domain knowledge (snippet from the RecSys programme and ACM abstract; ACM page returned 403). [P — industry talk abstract] — [RecSys 2019 Industry Session 2](https://recsys.acm.org/recsys19/industry-session-2/); [ACM DL](https://dl.acm.org/doi/10.1145/3298689.3346960)
- **Home Depot, "Product collection recommendation in online retail" (Kouki, Fountalis, Vasiloglou, Yan, Ahsan, Al Jadda, Qu; RecSys 2019, old):** candidate collections are built by combining the product hierarchy with transaction data or domain knowledge; statistics come from about 28M online transactions with 46M product purchases between 1 Jan 2018 and 31 Mar 2019 (snippet). [P] — [ACM DL](https://dl.acm.org/doi/10.1145/3298689.3347003)
- **Customer pain point stated by Home Depot (2020, old):** finding all the products that form a collection for projects such as a bathroom or kitchen renovation (snippet). [T] — [Forbes, 17 Oct 2020](https://www.forbes.com/sites/cognitiveworld/2020/10/17/how-home-depot-is-enhancing-the-ecommerce-experience-with-ai/)
- **Home Depot + Google Cloud, 11 Jan 2026:** (a) "Magic Apron" assistant — customers describe a project in plain language (from a leaky faucet to a kitchen remodel) and get advice and product recommendations; store mode is tied to real-time local store inventory and aisle/bay location; (b) **AI materials lists for pros** — the pro describes a project by voice or text or uploads an existing product list, and the agent builds a grouped materials list and suggests missing items the job needs; beta November 2025, national rollout January 2026; stated benefit is faster quoting. No effect numbers are given. The release does not claim automatic quantity calculation. [F] — [Google Cloud press release](https://www.googlecloudpresscorner.com/2026-01-11-The-Home-Depot-and-Google-Cloud-Launch-Agentic-AI-Tools-to-Help-Customers-and-Associates-Bring-Projects-from-How-to-to-Done)
- **Adeo (Leroy Merlin, Weldom):** built a knowledge graph and uses LLM-based named-entity recognition and entity linking to connect its DIY how-to articles — previously not linked to products — to the products, tools and materials they mention, so that relevant products can be recommended to the reader of an article. [F/T — Adeo Tech x Artefact engineering blog] — [Medium](https://medium.com/artefact-engineering-and-data-science/enriching-the-diy-experience-how-adeo-uses-ai-to-connect-content-and-knowledge-e3db05fbb011)
- **Leroy Merlin knowledge graph for recommendations (vendor case study):** content mined included Leroy Merlin's blog, product sheets, YouTube subtitles and industry blogs to propose ontology elements. [V] — [Lettria](https://www.lettria.com/case-study/leroy-merlin-knowledge-graph-product-recommendations)
- **Leroy Merlin Russia (now Lemana PRO):** a 2021 Habr article on the company's IT history mentions that its product publication platform contained microservices responsible for recommendations — no detail on logic (old; snippet). [F] — [Habr 540168](https://habr.com/ru/post/540168)
- **Lemana PRO product card today** carries a "С этим товаром покупают" (bought with this product) block, described as suited to selling related goods; the description comes from an agency's overview of Lemana PRO's retail-media platform launched in autumn 2024, i.e. the block is also an advertising placement (snippet). [V] — [Molinos](https://molinos.ru/about/blog/novyy-kanal-prodazh-dlya-tovarov-v-nishe-remonta-i-stroitelstva-obzor-lemana-pro)
- **Petrovich (Russia), 2024 results:** revenue 181 bn RUB (+17%); website + contact centre = 50% of wholesale and retail sales; 3.7M site orders; ecosystem "Petrovich.Dom" revenue +50%, with the **repair calculator** named among its most requested services (alongside door installation and flooring laying). No description of how the calculator or recommendations work. [T — company results as reported by trade press] — [Retail.ru, 24 Feb 2025](https://www.retail.ru/news/petrovich-vyruchka-v-2024-godu-sostavila-rekordnye-181-mlrd-rubley-24-fevralya-2025-261273/)
- **Quantity calculators — how the arithmetic is done (manufacturer tools, not retailers):** inputs are tiled area, tile length/width/thickness, joint width and adhesive coverage rate; outputs are adhesive in kg and bags and grout in kg; an offcut allowance of around 10% is commonly added; coverage figures differ between sources, so the product's own coverage rate must be used (snippets). — [calculate.co.nz](https://www.calculate.co.nz/tile-adhesive-grout-calculator.php); [Sika](https://www.sika.com/en/knowledge-hub/tile-grout-adhesive-calculator.html)
- **UX guidance on grouping by project:** Baymard recommends prioritising cross-sells with the same theme or use case (seasonal or project-based groupings) and labelling them ("Frequently Bought Together", "Other Products in this Collection") so users understand why they are shown. [UX, 2021] — [Baymard](https://baymard.com/research-articles/product-recommendations-cart)

### Inferences
- The three IRG kinds map cleanly onto building materials: accessories/consumables (drill -> bits; tile -> adhesive, grout, spacers, primer), collections (tile series: wall + floor + border; sanitary ware series; profile systems), parts/spares. They need different data: accessories from category mapping + co-purchase, collections from catalogue attributes (same collection/series/brand), parts from manual links.
- A project spans several orders, so same-basket co-occurrence under-counts project complements; counting co-purchases per customer within a time window (for example 30–60 days) captures "tile now, grout next week". This is the "bought X also bought Y" link type in Sceptre, as opposed to "frequently bought together" (same basket).
- A quantity calculator is the domain's strongest cross-sell device because it produces both the complement list and the quantities; it needs per-product coverage attributes (kg/m², m² per pack), which is an attribute-data problem rather than a recommendation-model problem.
- The 2026 Home Depot launch shows the direction: project intent is captured explicitly (the customer says what the job is) instead of being inferred from clicks. No published evidence yet that it outperforms curated project kits.

### Gaps
- No first-party engineering article, paper or talk on recommendations was found for Lemana PRO / Leroy Merlin Russia, Petrovich, OBI, Hornbach, Kingfisher/B&Q or Lowe's (searches in English and Russian, including Habr). "I found no reliable sources" applies to all of them; their on-site features can be observed but their methods are not published.
- Retailer-hosted calculators (Home Depot, Leroy Merlin, B&Q) were not retrieved; only manufacturer/third-party calculators were.
- No published project-intent *detection* paper (inferring the project from behaviour) from Home Depot or Lowe's was retrieved; the full abstract of the Home Depot RecSys 2019 talk could not be fetched, so whether it discusses project intent beyond IRG is unconfirmed.
- No effect sizes for collections, kits or calculators in DIY were found.

---

## 5. Professional / B2B customers (contractors, foremen)

### Takeaway
For pros, the retailers' "recommendation" features are mostly not predictive at all: reorder from purchase history, saved lists of regular items, quotes and volume pricing. The big chains keep extending exactly these tools in 2025–2026, which signals where the value is for repeat professional buyers.

### Cited Findings
- **Lowe's, press release 17 Feb 2026:** pro tools on Lowes.com and the app include online quoting from the job site, order tracking and full purchase history, spend reports and itemized billing by job or client, a **"Buy It Again" reordering tool**, purchase authorization for crews, QuickBooks/Quicken integration, a digital wallet; separately, direct-to-jobsite delivery from participating suppliers and bulk discounts / customized quotes on large orders. No usage numbers. [F] — [Lowe's Newsroom](https://corporate.lowes.com/newsroom/press-releases/lowes-strengthens-pro-experience-small-medium-size-pro-02-17-26)
- **Lowe's earlier "MVPs Business Tools":** "Buy it Again" prompt for frequently purchased items, sortable by frequency, recency and price of purchase; online quotes with price guaranteed for seven days; savings on eligible orders of $1,500 or more for Silver tier and above (snippet). [T] — [Modern Distribution Management](https://www.mdm.com/news/technology/lowes-launches-digital-mvp-business-tools-for-pros/)
- **Home Depot Pro (first-party page):** pros can create product lists for their most-used items, view purchase history, track orders and export purchases to Excel; jobs can be handled from planning and pricing to purchasing on one platform (snippet). [F] — [Home Depot Pro Resource Center](https://www.homedepot.com/c/pro_resource_center)
- **Home Depot volume pricing (third-party descriptions; figures inconsistent, verify before use):** reported as 4,000+ eligible items, up to 30% off in categories such as drywall, insulation and conduit, with a $1,500 qualifying total that can mix categories (snippet). [T] — [ServiceTitan](https://www.servicetitan.com/blog/home-depot-pro-xtra)
- **Home Depot purchase and list data are synced hourly into contractor software (Buildertrend)** — pros use purchase history for job costing, not only for reordering (snippet). [T/V] — [Buildertrend](https://conference.buildertrend.com/integration/pro-xtra/)
- **Home Depot AI materials list (Jan 2026)** is explicitly a pro feature: describe the job or upload a list, receive a grouped list plus suggested missing items. [F] — [Google Cloud press release](https://www.googlecloudpresscorner.com/2026-01-11-The-Home-Depot-and-Google-Cloud-Launch-Agentic-AI-Tools-to-Help-Customers-and-Associates-Bring-Projects-from-How-to-to-Done)
- **Weight of the segment in the CIS market:** at Petrovich B2B is 45% of revenue; customer groups named are retail buyers, foremen (прорабы) and corporate clients; loyalty programmes target both B2C buyers and professional builders and have 900 thousand participants; the wholesale unit serves over 3,500 large construction sites. [T] — [Retail.ru, 24 Feb 2025](https://www.retail.ru/news/petrovich-vyruchka-v-2024-godu-sostavila-rekordnye-181-mlrd-rubley-24-fevralya-2025-261273/)
- **Repeat-biased recommenders suit high-repeat users and hurt low-repeat ones:** on TaFeng, users with repeat ratio above 0.8 are 5.5% of users but contribute 18.8–36.8% of average performance; for users with repeat ratio 0–0.2 some repeat-biased methods fall below global popularity. [P] — [arXiv 2109.14233](https://ar5iv.labs.arxiv.org/html/2109.14233)

### Inferences
- Feature order that matches what the chains ship for pros: (1) "repeat this order" on an order; (2) "your regular items" (personal frequency list, sortable by frequency / recency); (3) saved lists per job or client; (4) missing-item suggestions against a list or cart (complement mapping applied to the whole basket); (5) volume-price nudges ("add N more to reach the bulk price").
- Pro behaviour differs from B2C in ways that matter to the model: large quantities (quantity should be pre-filled from the last order, not 1), the same SKUs across jobs (high repeat ratio), strong brand/SKU loyalty (a substitute is welcome only when the regular SKU is out of stock), price sensitivity. These statements are inferences from the feature sets above; no retrieved source measures them.
- A customer role flag (regular buyer vs. foreman) is a cheap and strong segmentation feature: repeat-heavy widgets for foremen, project/complement widgets for regular buyers.
- Pros' baskets contaminate co-purchase statistics for B2C complement mining (very large mixed baskets); computing complements separately per segment, or capping basket size, is advisable.

### Gaps
- No published measurements of pro vs. DIY behaviour (repeat ratio, basket size, SKU loyalty) in home improvement were found; nothing on "pro-price-aware" recommendation models.
- No adoption or revenue numbers for Buy It Again / lists at Lowe's or Home Depot.
- Nothing published on how Petrovich or Lemana PRO serve foremen digitally beyond loyalty programmes.

---

## 6. Compatibility and attribute constraints

### Takeaway
Compatibility-dependent accessories are the most valued cross-sell and the most damaging when wrong; the documented industry practice is a hybrid — manually curated anchor–accessory links plus category-level constraints, with behavioural data used for ranking inside those constraints. No retailer has published a rule engine for technical compatibility of building materials.

### Cited Findings
- **Baymard:** accessories needed to use or install the product (batteries, mounting hardware, compatible cases) should take precedence over all other suggestions; users see them as "good service" rather than a sales pitch. [UX, 2021] — [Baymard](https://baymard.com/research-articles/product-recommendations-cart)
- **One bad suggestion poisons the block:** a single questionable recommendation can make users distrust and ignore the whole set; hence show a dynamic number of items — only those with high relevance. [UX, 2021] — [Baymard](https://baymard.com/research-articles/product-recommendations-cart)
- **Baymard guideline #2667 "Showcasing compatible parts"** exists as a separate guideline (first observed Feb 2024, updated Sep 2025): users find it difficult to locate products specifically designed to be used with the currently viewed product (snippet; guideline body is paywalled). [UX] — [Baymard](https://baymard.com/guidelines/2667-showcasing-compatible-parts)
- **Home Depot:** manually entered anchor–accessory SKU relationships in an IRG database; at most one accessory SKU per accessory category per anchor (snippet). [F — patent application] — [FreePatentsOnline](https://www.freepatentsonline.com/y2020/0104898.html)
- **Home Depot states the difficulty directly:** recommending accessories, collections and parts requires anything from visual compatibility (style match within a collection) to functional understanding (snippet). [P — talk abstract, 2019, old] — [ACM DL](https://dl.acm.org/doi/10.1145/3298689.3346960)
- **Collections from hierarchy + transactions or domain knowledge** (Home Depot, 2019, old; snippet). [P] — [ACM DL](https://dl.acm.org/doi/10.1145/3298689.3347003)
- **Compatibility labels in research are expert-made or LLM-annotated**, not derived from purchases: the survey lists compatibility labels manually marked by experts and, more recently, annotated by LLMs. [P — survey, 2024] — [arXiv 2403.16135](https://ar5iv.labs.arxiv.org/html/2403.16135)
- **Knowledge-graph route (Adeo):** entities extracted from how-to content are linked to catalogue products, which gives "this job needs these tools and materials" relations independent of purchase data. [F/T] — [Medium, Adeo Tech x Artefact](https://medium.com/artefact-engineering-and-data-science/enriching-the-diy-experience-how-adeo-uses-ai-to-connect-content-and-knowledge-e3db05fbb011)

### Inferences
- A layered source of truth is the pattern: manual links (highest priority, always shown first) -> attribute rules (equal diameter / thread / collection / base) -> category-level complement map ranked by co-purchase. Behavioural data alone cannot guarantee that a 20 mm fitting is offered for a 20 mm pipe.
- Attribute rules require structured, typed attributes (number with unit, list with fixed options) shared across the categories being matched — e.g. the same "diameter" attribute on pipes and fittings, the same "collection" attribute on wall and floor tiles. A store with a global attribute dictionary attached to item categories can express rules as "target category X where attribute A equals the anchor's A". This is an inference about implementation; no source prescribes it.
- Examples of rule types in this domain (illustrative, not from a source): equal-value (pipe and fitting diameter, thread size, screw gauge and anchor), same-collection/colour (tile series, paint tint), base match (water-based primer under water-based paint), system match (drywall profile width and board type; power-tool battery platform).
- When no compatible in-stock item exists, showing nothing is better than a near-miss (the "one questionable recommendation" finding).

### Gaps
- No public description of an attribute-compatibility rule engine at any DIY retailer (Home Depot, Lowe's, Leroy Merlin, Kingfisher, OBI, Hornbach, Petrovich) was found; the Home Depot patent text could not be fetched in full, so how it ranks or validates accessory candidates beyond the snippet is unknown.
- The body of Baymard's compatible-parts guideline is paywalled.
- No data on return rates or complaints caused by incompatible recommendations.

---

## 7. Placement and business value

### Takeaway
Credible, controlled numbers are small and placement-specific (single-digit to low-double-digit relative lifts); the famous "35% of Amazon revenue" is an unsourced consultancy estimate that an academic field experiment contradicts. UX research says the cart is where irrelevant recommendations are most common and where compatibility-driven add-ons are most welcome; forced cross-sell steps backfire.

### Cited Findings
- **"35% of Amazon" provenance:** attributed to McKinsey (2013): 35% of what consumers purchase on Amazon and 75% of what they watch on Netflix come from product recommendations; later sources repeat it with shifting wording (purchases / sales / revenue). No methodology was located. [T — secondary citations] — [UF Warrington](https://warrington.ufl.edu/news/how-valuable-are-online-product-recommendations/); [Berkeley iSchool](https://www.ischool.berkeley.edu/node/8547)
- **Academic counter-estimate:** Kumar (Univ. of Florida) and Hosanagar (Wharton), *Information Systems Research* (2018/2019, old): randomized experiment on a fashion retailer's site, more than two million product page views from nearly a million sessions, treatment with recommendations vs. control without. Sales of recommended products +9%, sales of the viewed (focal) product −1.9%, overall product sales **+11%**; popular, highly linked products gained more, less popular ones did worse. Kumar calls the McKinsey-style estimates "hard to believe": recommended items are often ones shoppers already know or could find by search, so attributing those sales to recommendations is inaccurate. [P — summarised by the university] — [UF Warrington](https://warrington.ufl.edu/news/how-valuable-are-online-product-recommendations/)
- **Buy again placement (Amazon, old):** +7.1% CTR on the personalized recommendations page when the Buy It Again widget replaced another widget; afterwards rolled out to other pages including the home page and the mobile app. CTR, not revenue. [P] — [Amazon Science PDF](https://cdn.amazon.science/40/e5/89556a6341eaa3d7dacc074ff24d/buy-it-again-modeling-repeat-purchase-recommendations.pdf)
- **Cart / added-to-cart:** 52% of benchmarked desktop sites show cross-sells there that are completely irrelevant or based only on what other customers bought; users quickly dismiss recommendations not obviously tied to what they are buying; irrelevant promotions are clutter, worse on mobile. [UX, 2021] — [Baymard](https://baymard.com/research-articles/product-recommendations-cart)
- **Interruptive cross-sell steps:** injected cross-sells requiring an active decision before the next checkout step are perceived as highly aggressive; 66% of users who had to pass a separate cross-sell step at Amazon showed extreme frustration (snippet). [UX] — [Baymard cross-sell benchmark](https://baymard.com/checkout-usability/benchmark/step-type/cross-sell)
- **Behavioural data alone is not enough:** "Customers Also Bought" should not be the only relevance signal; combine user-specific data (history, cart contents, profile) with general data (category relationships). [UX, 2021] — [Baymard](https://baymard.com/research-articles/product-recommendations-cart)
- **Vendor number for a DIY retailer (unverified):** Dynamic Yield's case study is titled "Leroy Merlin Gains 32% Purchases with ML Recommendations" (reported as Leroy Merlin South Africa; recommendations also shown after add-to-cart). Page body could not be fetched — metric, baseline and test design unknown. [V] — [Dynamic Yield](https://www.dynamicyield.com/case-studies/leroymerlin/)

### Inferences
- Reasonable expectation setting: a relative lift of a few percent to roughly 10% in the affected metric from a well-placed, relevant block; anything like "30%+ of revenue" is an attribution figure (share of orders that touched a widget), not incremental revenue.
- Attribution vs. incrementality is especially misleading for "buy again": the customer would have re-bought most of those items anyway via search; the honest metrics are time-to-reorder, order frequency and basket size under an A/B test.
- Likely ranking of placements for a building-materials store, combining the evidence: (1) product page / add-to-cart "you will also need" with compatible consumables and accessories (highest relevance, perceived as service); (2) cart "you may have forgotten" computed against the whole basket; (3) home / account "buy again" for repeat customers and pros; (4) post-purchase follow-ups for multi-order projects; (5) generic "for you" on the home page (weakest signal for one-off renovators). This ordering is an inference; no source ranks placements for home improvement with controlled data.
- Popularity effects cut both ways (Kumar & Hosanagar): co-purchase recommenders push already-popular items and may depress long-tail items — relevant when the store wants to promote private label or new SKUs.

### Gaps
- The original McKinsey article ("How retailers can keep up with consumers", Oct 2013, as commonly cited) could not be fetched (timeout), so its exact wording and the absence of a methodology are reported from secondary sources only.
- No independently verified, controlled revenue numbers per placement exist for any home-improvement retailer; all DIY-specific numbers found are vendor marketing.
- No data on post-purchase (email / push) recommendation performance in this domain.

---

## 8. Business rules layered on top of the model

### Takeaway
Published evidence supports a small set of rules — diversity across complementary categories with one item per category, a dynamic (possibly zero) number of items, no substitutes late in the funnel, clear labels, "not too early" for repeats, and local-inventory grounding; margin / private-label boosts and price-sanity rules are common practice but not documented by any retrieved first-party source.

### Cited Findings
- **Diversity across categories:** an ideal complementary recommendation "should consider both relevance and diversity"; P-Companion picks products from multiple predicted complementary types. [P] — [arXiv 2403.16135](https://ar5iv.labs.arxiv.org/html/2403.16135); [Amazon Science](https://amazon.science/publications/p-companion-a-principled-framework-for-diversified-complementary-product-recommendation)
- **One item per accessory category** (Home Depot patent; snippet). [F] — [FreePatentsOnline](https://www.freepatentsonline.com/y2020/0104898.html)
- **Dynamic number of suggestions:** show only as many as are highly relevant; a single strong suggestion gets more attention than one surrounded by weak ones. [UX, 2021] — [Baymard](https://baymard.com/research-articles/product-recommendations-cart)
- **No alternatives in the cart; label every block** ("Frequently Bought Together", "Other Products in this Collection"); compatibility-dependent items first. [UX, 2021] — [Baymard](https://baymard.com/research-articles/product-recommendations-cart)
- **Match promotions to the order context:** Baymard's negative example is Lowe's showing an 18-month financing offer on a $6 order. [UX, 2021] — [Baymard](https://baymard.com/research-articles/product-recommendations-cart)
- **Eligibility gate and timing for repeats:** only repeat-purchasable products (RCP above threshold); models that recommend "too early" after a purchase drew negative customer feedback and were not launched. [P, old] — [Amazon Science PDF](https://cdn.amazon.science/40/e5/89556a6341eaa3d7dacc074ff24d/buy-it-again-modeling-repeat-purchase-recommendations.pdf)
- **Local inventory grounding:** Home Depot's assistant in store mode is connected to real-time local store inventory and product locations. [F, Jan 2026] — [Google Cloud press release](https://www.googlecloudpresscorner.com/2026-01-11-The-Home-Depot-and-Google-Cloud-Launch-Agentic-AI-Tools-to-Help-Customers-and-Associates-Bring-Projects-from-How-to-to-Done)
- **Signals reported for Home Depot personalization (secondary source, low reliability):** browsing behaviour, purchase history, inferred project type, local availability, weather (snippet). [T] — [DigitalDefynd](https://digitaldefynd.com/IQ/home-depot-using-ai-case-studies/)
- **Recommendation blocks double as retail-media inventory** (Lemana PRO's product-card blocks are sold through its advertising platform; snippet) — sponsored items compete with organic complements. [V] — [Molinos](https://molinos.ru/about/blog/novyy-kanal-prodazh-dlya-tovarov-v-nishe-remonta-i-stroitelstva-obzor-lemana-pro)
- **Popularity concentration:** recommendations raised sales of popular, highly linked products and lowered those of less popular ones. [P, old] — [UF Warrington](https://warrington.ufl.edu/news/how-valuable-are-online-product-recommendations/)

### Inferences
- Rule checklist that follows from the above plus domain logic (items marked * have no direct published source and are standard practice / inference):
  1. Active, purchasable and **in stock** only*; where stock is per branch, in stock at the customer's delivery or pickup branch* (grounded by Home Depot's local-inventory design).
  2. Exclude items already in the cart; exclude recently purchased durables and their same-category substitutes*.
  3. Repeat block: eligible categories only, hidden for a minimum period after the last purchase.
  4. Complements: manual / compatibility links first, then category-mapped items; one per target category; several categories.
  5. Price sanity*: an accessory should not cost more than the anchor (direction rule), and should sit in a comparable quality tier — do not offer a premium blade for a budget tool or vice versa.
  6. Show zero items rather than weak ones; keep a minimum co-purchase support before a pair is eligible.
  7. Margin / private-label boost as a tie-breaker inside an already-relevant candidate set, never as a candidate source*.
  8. Suggested quantity and unit*: pre-fill from a calculator (coverage per m²) or, for repeat items, from the customer's last / median quantity.
  9. Label the block by its reason ("needed for installation", "bought with this", "you bought this before").
- Sponsored placements inside "bought together" blocks weaken trust if they break compatibility; keep compatibility rules above monetization.

### Gaps
- No first-party source documents margin or private-label boosting, price-range rules or quantity suggestions in recommendation blocks for any home-improvement retailer — these remain unsourced practice.
- No published guidance on exclusion windows for purchased durables.
- No evidence on how branch-level stock filtering changes recommendation performance.

---

## 9. What is different about this domain (vs. fashion, media, grocery)

### Takeaway
The demand unit is a project with technically constrained complements, most items are either one-off durables or bulk consumables, and a professional segment re-buys the same SKUs — so "similar items" taste modelling matters less, while complement structure, compatibility, quantities, repeat lists and stock matter more.

### Cited Findings
- Home Depot itself frames the domain's key recommendation type as Item Related Groups — accessories, collections, parts — with challenges from visual compatibility to functional understanding (snippet). [P — talk abstract, 2019, old] — [RecSys 2019 Industry Session 2](https://recsys.acm.org/recsys19/industry-session-2/)
- Completing a project's collection (bathroom, kitchen) is named as the customer pain point (snippet). [T, 2020, old] — [Forbes](https://www.forbes.com/sites/cognitiveworld/2020/10/17/how-home-depot-is-enhancing-the-ecommerce-experience-with-ai/)
- The newest tools ask for the project explicitly and return a grouped materials list with missing items. [F, Jan 2026] — [Google Cloud press release](https://www.googlecloudpresscorner.com/2026-01-11-The-Home-Depot-and-Google-Cloud-Launch-Agentic-AI-Tools-to-Help-Customers-and-Associates-Bring-Projects-from-How-to-to-Done)
- The professional segment is large (Petrovich: B2B 45% of revenue, foremen a named customer group) and is served with reorder / list / quote tools (Lowe's, Home Depot). [T/F] — [Retail.ru](https://www.retail.ru/news/petrovich-vyruchka-v-2024-godu-sostavila-rekordnye-181-mlrd-rubley-24-fevralya-2025-261273/); [Lowe's Newsroom](https://corporate.lowes.com/newsroom/press-releases/lowes-strengthens-pro-experience-small-medium-size-pro-02-17-26)
- Public repeat-purchase benchmarks are grocery-only (repeat ratios 0.19–0.60), so their results transfer only to the consumable / pro part of a DIY assortment. [P] — [arXiv 2109.14233](https://ar5iv.labs.arxiv.org/html/2109.14233)
- Content (how-to articles, videos) is a first-class data source in DIY: Adeo links how-to content to products through a knowledge graph. [F/T] — [Medium, Adeo Tech x Artefact](https://medium.com/artefact-engineering-and-data-science/enriching-the-diy-experience-how-adeo-uses-ai-to-connect-content-and-knowledge-e3db05fbb011)

### Inferences
- Compared with fashion: style similarity matters only inside collections (tiles, sanitary ware); elsewhere function and dimension compatibility dominate; returns from a wrong recommendation are heavy and costly (bulk goods).
- Compared with media: there is no "consume more of the same" loop; after a durable purchase the similar-items signal is actively wrong.
- Compared with grocery: baskets are less frequent and far more heterogeneous; replenishment is job-driven rather than consumption-driven; quantities are computed from area/volume instead of habit.
- Data is sparse per customer (a household renovates rarely), so item-to-item and category-to-category structures learned from all orders, plus curated links, carry more weight than per-user collaborative filtering; per-user personalisation pays off mainly for the repeat-buying professional segment.

### Gaps
- No comparative study (same method across DIY vs. grocery vs. fashion) was found; the contrasts above are reasoned from the cited feature sets and papers, not measured.
- Russian-language first-party engineering sources on DIY recommendations (Lemana PRO, Petrovich, OBI Russia, VseInstrumenti) were searched for and not found.
