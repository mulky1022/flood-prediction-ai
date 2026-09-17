# Model Decision Threshold & Operating Trade-Off Analysis

## 1. Overview
In binary classification systems for disaster early warning, the choice of classification decision threshold ($T \in [0.0, 1.0]$) represents a direct trade-off between **Sensitivity (Recall)** and **Specificity (Precision)**.

---

## 2. Threshold Performance Matrix

| Threshold | Precision | Recall | F1-Score | TP | FP | TN | FN | False Negative Rate (FNR) |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **0.10** | 18.54% | **100.00%** | 0.3128 | 1,993 | 8,758 | 9,249 | 0 | **0.00%** |
| **0.20** | 35.56% | **99.75%** | 0.5243 | 1,988 | 3,603 | 14,404 | 5 | **0.25%** |
| **0.30** | 60.55% | **98.90%** | 0.7511 | 1,971 | 1,284 | 16,723 | 22 | **1.10%** |
| **0.35** | 72.28% | **97.49%** | 0.8302 | 1,943 | 745 | 17,262 | 50 | **2.51%** |
| **0.40** | 82.40% | **95.38%** | 0.8842 | 1,901 | 406 | 17,601 | 92 | **4.62%** |
| **0.45** | 89.90% | **92.47%** | 0.9117 | 1,843 | 207 | 17,800 | 150 | **7.53%** |
| **0.50** | 95.04% | **87.51%** | 0.9112 | 1,744 | 91 | 17,916 | 249 | **12.49%** |
| **0.60** | 99.05% | **72.96%** | 0.8402 | 1,454 | 14 | 17,993 | 539 | **27.04%** |
| **0.70** | 99.90% | **50.43%** | 0.6702 | 1,005 | 1 | 18,006 | 988 | **49.57%** |
| **0.80** | 100.00% | **27.85%** | 0.4356 | 555 | 0 | 18,007 | 1,438 | **72.15%** |
| **0.90** | 100.00% | **8.43%** | 0.1555 | 168 | 0 | 18,007 | 1,825 | **91.57%** |

---

## 3. Engineering & Operational Trade-Offs

### A. Low Thresholds ($T \le 0.35$) — High Sensitivity / Early Warning
* **Advantage**: Maximizes Recall ($> 97\%$) and minimizes missed disasters ($\text{FNR} < 2.5\%$).
* **Trade-off**: Higher false positive rate, which can lead to warning fatigue if used for mass public broadcasts.

### B. Balanced Thresholds ($T \approx 0.45 - 0.50$) — Maximum F1-Score
* **Advantage**: Optimizes harmonic balance between Precision ($90-95\%$) and Recall ($87-92\%$).
* **Trade-off**: Results in ~7–12% false negatives under edge conditions.

### C. High Thresholds ($T \ge 0.70$) — High Certainty / Evacuation Trigger
* **Advantage**: Near-zero false alarms (Precision $> 99.9\%$).
* **Trade-off**: Misses roughly half of impending events (Recall $< 50\%$).

---

## 4. Policy Recommendation for MVP
In accordance with system design principles:
1. **Raw Probability Primary**: The core API returns the continuous probability $P(\text{Flood} = 1)$ as the primary scientific output.
2. **Multi-Tier Prototype Display**: Thresholds are presented as prototype early-warning tiers (e.g., Low $< 0.35$, Moderate $0.35–0.60$, High $0.60–0.80$, Critical $\ge 0.80$) without claiming certified scientific absolute certainty.
