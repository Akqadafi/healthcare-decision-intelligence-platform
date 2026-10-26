# Worked example: compare Apache County tracts

Use study **az-tract-v1**, ACS **2019–2023**, and CDC PLACES **2025 release**.
Allow about 5–10 minutes to read and explore; this is a human-use estimate.
The verified automated walkthrough took **43.8 seconds** on October 24, 2026,
including model switching and both downloads; this is not a human reading time.

1. Open the original dashboard and choose **Explore census tracts**. Click **Reset
   tract controls**. Expect **1,765 tracts shown**, including **35 excluded**. The
   selected model is K-means with two groups. Read the source periods and the note
   explaining that filters do not retrain the model.
2. In **Counties**, clear the existing selections and select **Apache**. Keep
   **All groups**, **Diabetes (%)**, range **0–100**, and both inclusion checkboxes
   selected. Expect **18 tracts shown**. The map and table now show Apache County.
3. In **First tract**, choose **04001942600**. In **Comparison tract**, choose
   **04001942700**. Both belong to **Group 2** in this saved model. Expected values:

| Measure | 04001942600 | 04001942700 |
|---|---:|---:|
| Modeled adult diabetes (%) | 21.5 | 20.4 |
| Modeled 95% interval | 19.4–23.6 | 18.4–22.5 |
| People below poverty (%) | 36.18 | 34.10 |

   The diabetes intervals overlap. These estimates do not establish a statistically
   supported difference between the two tracts. Poverty values are rounded here;
   the table/download retain additional precision.
4. Read **Statewide profile medians**. Group 2's diabetes median is **14.35%**, compared
   with **10.00%** for Group 1. Both selected tracts exceed Group 2's median. This is
   a useful reminder that group summaries do not describe every member exactly.
5. Open **Stability & methods**. Find `kmeans_k2`: silhouette **0.4361**, median
   subsample ARI **0.9911**, minimum feature-removal ARI **0.8146**. The grouping is
   consistent under these checks, but the checks do not represent patient-level
   accuracy or uncertainty in the health estimates.
6. Change **Clustering method** to **Ward hierarchical**, keeping two groups. Expect
   an exploratory-comparison warning. `ward_k2` has silhouette **0.4479**, but median
   subsample ARI **0.6233**. Better separation alone did not make this the more stable
   choice. Group numbers may change meaning between methods. Switch back to **K-means**.
7. Open **Downloads & help** and download the filtered CSV and receipt. Expect **18
   rows**, model **kmeans_k2**, county selection **Apache**, and study **az-tract-v1**
   in the receipt. Preserve both files together. The receipt's hash identifies the
   downloaded CSV; its model manifest identifies the saved analysis.
8. Try a narrower measure range or another county, then reset when finished. If no
   rows match, the page explains how to recover. Returning to **Explore counties**
   takes you back to the separate county planning model.

Example finding: “In the saved two-group model, both selected Apache County tracts
belong to Group 2 and have modeled diabetes estimates above that group's statewide
tract median. Their uncertainty intervals overlap, so I would not infer a reliable
difference between their estimates from this comparison alone.”

Example limitation: “The health estimates are modeled, and their sources include
ACS inputs. Cluster stability does not validate the estimates or establish causes.”

Verified screenshots: [overview](../evidence/tract-dashboard/overview.png),
[Apache example](../evidence/tract-dashboard/apache.png), and
[downloads](../evidence/tract-dashboard/downloads.png). The browser-check receipt records
the observed controls, exported row count, checksum verification, and elapsed time.
