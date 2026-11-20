"""Inference for one category: the same feature construction, RL episode and privacy score as the notebooks."""
import json
import math
import os
import threading

import joblib
import numpy as np

MODEL_DIR = os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "models"))

CATEGORY_LABELS = {
    "education": "Education & Reference",
    "games": "Games",
    "lifestyle_health": "Lifestyle & Health",
    "media_entertainment": "Entertainment & Media",
    "productivity_tools": "Productivity & Tools",
    "social_communication": "Social & Communication",
}

# Dataset genre -> category key (same BROAD_CATEGORY_MAP as the Borda-Garrett weights).
GENRE_TO_CATEGORY = {
    "Education": "education", "Books & Reference": "education",
    "Arcade & Action": "games", "Brain & Puzzle": "games", "Casual": "games", "Cards & Casino": "games",
    "Racing": "games", "Sports Games": "games",
    "Travel & Local": "lifestyle_health", "Personalization": "lifestyle_health", "Lifestyle": "lifestyle_health",
    "Health & Fitness": "lifestyle_health", "Sports": "lifestyle_health", "Transportation": "lifestyle_health",
    "Shopping": "lifestyle_health", "Medical": "lifestyle_health", "Weather": "lifestyle_health",
    "Entertainment": "media_entertainment", "Media & Video": "media_entertainment",
    "Music & Audio": "media_entertainment", "Comics": "media_entertainment", "Photography": "media_entertainment",
    "Tools": "productivity_tools", "Business": "productivity_tools", "Finance": "productivity_tools",
    "Productivity": "productivity_tools", "Libraries & Demo": "productivity_tools",
    "Social": "social_communication", "Communication": "social_communication",
    "News & Magazines": "social_communication",
}

# Risk a fully trusted app converges to (Play Store reputation adjustment).
TRUST_FLOOR = 0.10

# Points a remaining risky combination adds to the data-access score (times its excess risk, 0-1).
DATA_ACCESS_COMBINATION_POINTS = 30

# Text views in the notebooks: name -> which text the view reads.
TEXT_VIEW_SOURCE = {"DescriptionTextRisk": "app", "DescriptionCharTextRisk": "app", "PackageTextRisk": "package"}


class CategoryModel:
    def __init__(self, key):
        with open(os.path.join(MODEL_DIR, f"{key}.json")) as f:
            self.cfg = json.load(f)
        blob = joblib.load(os.path.join(MODEL_DIR, f"{key}.joblib"))
        self.risk_model = blob["risk_model"]
        self.text_models = blob["text_models"]
        self.q_table = blob["q_table"]
        c = self.cfg
        self.key, self.rl = key, c["rl_features"]
        self.raw_columns = set(c["raw_permission_columns"])
        self.raw_to_group = {col: g for g, cols in c["permission_column_map"].items() for col in cols}
        self.clf_agg = [self.raw_to_group.get(p) for p in c["clf_permission_features"]]
        self.max_weight = max(c["weight_map"].get(p, 0.0) for p in self.rl) or 1.0
        self._cache = {}

    # ------------------------------------------------------------------ features
    def individual_risk(self, perm):
        return self.cfg["weight_map"].get(perm, 0.0) / self.max_weight

    def build_inputs(self, app):
        """Return (requested dict, metadata vector, notes) for an app description dict."""
        c = self.cfg
        raw = [p for p in app.get("permissions", []) if p in self.raw_columns]
        unknown = [p for p in app.get("permissions", []) if p not in self.raw_columns]
        raw_set = set(raw)
        added = []
        for group in app.get("permission_groups", []):
            cols = c["permission_column_map"].get(group, [])
            if cols and not raw_set.intersection(cols) and group in c["representative_raw"]:
                raw_set.add(c["representative_raw"][group])
                added.append(c["representative_raw"][group])

        requested = {g: int(bool(raw_set.intersection(cols))) for g, cols in c["permission_column_map"].items()}
        requested.update({p: int(p in raw_set) for p in c["clf_permission_features"]})

        n_ratings = max(float(app.get("num_ratings") or 0.0), 0.0)
        price = float(app.get("price") or 0.0)
        d = sum(1 for p in raw_set if p.endswith("(D)"))
        s = sum(1 for p in raw_set if p.endswith("(S)"))
        description = app.get("description") or ""
        name = app.get("app_name") or ""
        app_text = name + " . " + description
        pkg_text = ((app.get("package") or "").replace(".", " ") + " "
                    + "".join(" " if ch in "{},." else ch for ch in (app.get("related_apps") or "")))
        text_risk = {}
        for view, (vec, lr) in self.text_models.items():
            text = app_text if TEXT_VIEW_SOURCE[view] == "app" else pkg_text
            text_risk[view] = float(lr.predict_proba(vec.transform([text]))[0, 1])

        values = {
            "Number of ratings": n_ratings, "Dangerous permissions count": float(d),
            "Safe permissions count": float(s), "Price": price, "Rating": float(app.get("rating") or 0.0),
            "PermissionCount": float(sum(requested[g] for g in c["permission_names"])),
            "DangerousToSafeRatio": min(max(d / (d + s + 1e-6), 0.0), 1.0),
            "LogNumRatings": math.log1p(n_ratings), "DescriptionLength": float(len(description)),
            "IsPaid": float(price > 0), **text_risk,
        }
        genre = app.get("genre")
        for g, col in zip(c["genres"], c["genre_features"]):
            values[col] = float(genre == g)
        metadata = np.array([values.get(m, 0.0) for m in c["metadata_features"]], dtype=float)
        notes = {"unrecognized_permissions": unknown, "assumed_permissions": added, "text_risk": text_risk,
                 "requested_raw": sorted(raw_set)}
        return requested, metadata, notes

    def classifier_risk(self, granted, requested, metadata):
        perm_part = []
        for p, agg in zip(self.cfg["clf_permission_features"], self.clf_agg):
            if agg is not None and agg in self.rl:
                perm_part.append(float(requested.get(p, 0) if granted.get(agg, 0) == 1 else 0))
            else:
                perm_part.append(float(requested.get(p, 0)))
        v = np.asarray(perm_part + list(metadata), dtype=float)
        key = v.tobytes()
        if key not in self._cache:
            if len(self._cache) > 50000:
                self._cache.clear()
            self._cache[key] = float(self.risk_model.predict_proba(v.reshape(1, -1))[0, 1])
        return self._cache[key]

    def interaction_risk(self, granted, requested):
        matched = []
        for r in self.cfg["rules"]:
            if not r["GrantedConditions"]:
                continue
            if any(int(requested.get(p, 0)) == 1 for p in r["NotRequestedConditions"]):
                continue
            if all(int(granted.get(p, 0)) == 1 for p in r["GrantedConditions"]):
                matched.append(r)
        if not matched:
            return 0.0, []
        return float(np.clip(max(r["ExcessRisk"] for r in matched), 0, 1)), matched

    def risk_band(self, p):
        return int(np.digitize(p, self.cfg["risk_bin_edges"]))

    # ------------------------------------------------------------------ RL episode
    def analyze(self, app, trust=0.0, reward_fallback=False):
        """trust in [0, 1) (Play Store reputation, see playstore.reputation) shrinks every classifier risk towards
        TRUST_FLOOR before it enters the RL state, the rewards and the privacy score.
        reward_fallback: in a state the Q-table never saw, choose the action with the higher immediate reward
        instead of the notebook's default (allow).  trust = 0 and reward_fallback = False is exactly the notebook."""
        c = self.cfg
        a, b, g, dc = c["alpha"], c["beta"], c["gamma"], c["denial_cost"]
        requested, metadata, notes = self.build_inputs(app)
        risk = lambda gr: (1 - trust) * self.classifier_risk(gr, requested, metadata) + trust * TRUST_FLOOR
        full = {p: requested.get(p, 0) for p in self.rl}
        full_risk = risk(full)
        band = self.risk_band(full_risk)
        mask = tuple(int(requested.get(p, 0)) for p in self.rl)

        granted = {p: 0 for p in self.rl}
        interaction, steps = 0.0, []
        for i, perm in enumerate(self.rl):
            state = (i, mask, tuple(granted[p] for p in self.rl), band)
            if not requested.get(perm, 0):
                continue
            q0, q1 = self.q_table.get((state, 0)), self.q_table.get((state, 1))
            seen = q0 is not None or q1 is not None
            util, ind = c["utility_map"][perm], self.individual_risk(perm)
            trial = {**granted, perm: 1}
            cls_allow = risk(trial)
            new_int, matched = self.interaction_risk(trial, requested)
            allow_reward = a * util - b * (0.5 * ind + 0.5 * cls_allow) - g * (new_int - interaction)
            deny_reward = -(a * util) * dc
            if seen or not reward_fallback:
                action = 1 if (q1 or 0.0) >= (q0 or 0.0) else 0      # the notebook's greedy action (ties -> allow)
            else:
                action = 1 if allow_reward >= deny_reward else 0     # unseen state: better immediate reward
            increase = new_int - interaction
            completed = [r for r in matched if increase > 0 and r["ExcessRisk"] == new_int]
            new_rules = [r["RuleNumber"] for r in completed]
            if action == 1:
                granted, interaction = trial, new_int
            steps.append({
                "permission": perm, "decision": "allow" if action == 1 else "deny", "learned_state": seen,
                "q_allow": q1, "q_deny": q0, "utility": util, "individual_risk": ind, "classifier_risk_if_allowed": cls_allow,
                "interaction_increase": increase,
                "reward_allow": allow_reward, "reward_deny": deny_reward, "rules_completed": new_rules,
                "rules_completed_permissions": [list(r["GrantedConditions"]) for r in completed],
                "raw_permissions": [p for p in c["permission_column_map"].get(perm, []) if p in notes["requested_raw"]],
            })

        granted_set = [p for p in self.rl if granted[p]]
        ind = float(np.mean([self.individual_risk(p) for p in granted_set])) if granted_set else 0.0
        cls_final = risk(granted)
        int_final, matched = self.interaction_risk(granted, requested)
        w = c["score_weights"]
        score = float(np.clip(w["individual"] * ind + w["classifier"] * cls_final + w["interaction"] * int_final, 0, 1))
        # Data access: share of the category's total Borda-Garrett weight the allowed permissions carry, plus the
        # excess risk of any combination left. Separate from the verdict: it measures reach, not maliciousness.
        total_weight = sum(c["weight_map"].get(p, 0.0) for p in self.rl) or 1.0

        def data_access(grants):
            combination, _ = self.interaction_risk(grants, requested)
            return min(100.0, 100 * sum(c["weight_map"].get(p, 0.0) for p in self.rl if grants.get(p)) / total_weight
                       + DATA_ACCESS_COMBINATION_POINTS * combination)

        access, access_all = data_access(granted), data_access(full)
        access_level = "Limited" if access < 25 else ("Moderate" if access < 50 else "Broad")
        uncontrolled = [p for p in notes["requested_raw"] if self.raw_to_group.get(p) not in self.rl]
        return {
            "category": c["category"], "category_key": self.key,
            "verdict": "malicious" if score > c["threshold"] else "benign",
            "privacy_score": score, "threshold": c["threshold"],
            "malicious_probability_all_allowed": full_risk, "risk_band": band,
            "malicious_probability_after_policy": cls_final,
            "individual_risk": ind, "interaction_risk": int_final,
            "data_access": {"score": round(access, 1), "level": access_level, "all_allowed": round(access_all, 1)},
            "triggered_rules": [{"rule": r["RuleNumber"], "conditions": r["ConditionsText"],
                                 "excess_risk": r["ExcessRisk"]} for r in matched],
            "decisions": steps,
            "allowed": granted_set,
            "denied": [s["permission"] for s in steps if s["decision"] == "deny"],
            "not_controlled_permissions": uncontrolled,
            "unrecognized_permissions": notes["unrecognized_permissions"],
            "assumed_permissions": notes["assumed_permissions"],
            "text_risk": notes["text_risk"],
            "coefficients": {"alpha": a, "beta": b, "gamma": g},
            "model": {"name": c["risk_model_name"], "rules": len(c["rules"]), "test_metrics": c["test_metrics"]},
        }


class Registry:
    """Loads category models lazily and keeps them in memory."""

    def __init__(self):
        self._models, self._lock = {}, threading.Lock()

    def available(self):
        return [k for k in CATEGORY_LABELS if os.path.exists(os.path.join(MODEL_DIR, f"{k}.json"))]

    def get(self, key):
        if key not in CATEGORY_LABELS:
            raise KeyError(key)
        with self._lock:
            if key not in self._models:
                self._models[key] = CategoryModel(key)
            return self._models[key]

    def config(self, key):
        with open(os.path.join(MODEL_DIR, f"{key}.json")) as f:
            return json.load(f)
