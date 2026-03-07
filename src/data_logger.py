import pandas as pd
from datetime import datetime
import json
import os

# ── Configuration ──────────────────────────────────────────────────────────────

STUDY_START        = "2026-02-18"
PROTOCOL_PATH      = "../protocol/schedule.json"
DATA_PATH          = "../data/Miura_Data.csv"

# Column names must match Shortcuts CSV output exactly
CSV_COLUMNS = [
    "timestamp",
    "mood",
    "agency",
    "metacognition",
    "melatonin_taken",
    "override_reason",
]

VALID_RANGES = {
    "mood":           (0, 100),
    "agency":         (0, 100),
    "metacognition":  (0, 100),
    "melatonin_taken": (0, 1),
}


# ── Protocol Loader ────────────────────────────────────────────────────────────

class StudyLogger:

    def __init__(self,
                 start_date_str: str = STUDY_START,
                 protocol_path:  str = PROTOCOL_PATH,
                 data_path:      str = DATA_PATH):

        self.start_date    = datetime.strptime(start_date_str, "%Y-%m-%d")
        self.protocol_path = protocol_path
        self.data_path     = data_path
        self.protocol      = self._load_protocol()

    def _load_protocol(self) -> dict:
        with open(self.protocol_path, "r") as f:
            return json.load(f)

    def get_study_day(self) -> int:
        return (datetime.now() - self.start_date).days + 1


# ── Manual Fallback Entry ──────────────────────────────────────────────────────

    def manual_entry(self):
        """
        Fallback: enter a data point manually if Shortcuts is unavailable.
        Mirrors the exact fields collected by the iOS automation.
        """
        day      = self.get_study_day()
        assigned = self.protocol.get(str(day))

        print(f"\n── N-of-1 Study: Day {day} ──")
        print(f"Protocol today: {'MELATONIN' if assigned == 1 else 'NO MELATONIN'}\n")

        def ask_score(prompt: str, lo: int = 0, hi: int = 100) -> float:
            while True:
                try:
                    val = float(input(f"{prompt} ({lo}-{hi}): "))
                    if lo <= val <= hi:
                        return val
                    print(f"  ✗ Must be between {lo} and {hi}.")
                except ValueError:
                    print("  ✗ Enter a number.")

        mood          = ask_score("Mood")
        agency        = ask_score("Agency: task progress feeling")
        metacognition = ask_score("Metacognition: awareness of current state")

        followed = input("Did you follow melatonin protocol? (y/n): ").strip().lower()
        if followed == "y":
            melatonin_taken = int(assigned)
            override_reason = "N/A"
        else:
            melatonin_taken = 1 - int(assigned)   # flipped
            override_reason = input("Override reason (optional): ").strip() or "N/A"

        entry = {
            "timestamp":       datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "mood":            mood,
            "agency":          agency,
            "metacognition":   metacognition,
            "melatonin_taken": melatonin_taken,
            "override_reason": override_reason,
        }

        self._save(entry)
        print("\n✓ Entry saved.\n")


# ── Data Validation ────────────────────────────────────────────────────────────

    def validate_data(self) -> pd.DataFrame:
        """
        Load Miura_Data.csv and run integrity checks.
        Prints a summary and returns the cleaned DataFrame.
        """
        if not os.path.isfile(self.data_path):
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

        df = pd.read_csv(self.data_path, header=None, names=CSV_COLUMNS)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        print(f"\n── Data Validation Report ──")
        print(f"Total rows : {len(df)}")
        print(f"Date range : {df['timestamp'].min()} → {df['timestamp'].max()}")
        print(f"Study days : {df['timestamp'].dt.date.nunique()}\n")

        issues = 0

        # Range checks
        for col, (lo, hi) in VALID_RANGES.items():
            if col not in df.columns:
                continue
            numeric = pd.to_numeric(df[col], errors="coerce")
            out     = numeric[(numeric < lo) | (numeric > hi)]
            if not out.empty:
                print(f"  ✗ {col}: {len(out)} out-of-range values")
                issues += 1

        # Missing values
        missing = df[CSV_COLUMNS[:5]].isnull().sum()
        if missing.any():
            print("  ✗ Missing values:")
            print(missing[missing > 0].to_string())
            issues += 1

        # Duplicate timestamps
        dupes = df[df["timestamp"].duplicated()]
        if not dupes.empty:
            print(f"  ✗ {len(dupes)} duplicate timestamps")
            issues += 1

        if issues == 0:
            print("  ✓ All checks passed.")

        # Add study day index
        df["study_day"] = (df["timestamp"] - self.start_date).dt.days + 1

        # Label A/B phase based on protocol
        # Phase A = days where assigned == 0 (baseline block)
        # Phase B = days where assigned == 1 (melatonin block)
        # Simple proxy: use melatonin_taken column
        df["melatonin_taken_num"] = pd.to_numeric(df["melatonin_taken"], errors="coerce")
        df["phase"] = df["melatonin_taken_num"].apply(
            lambda x: "B_melatonin" if x == 1 else "A_baseline"
        )

        print(f"\nPhase distribution:")
        print(df["phase"].value_counts().to_string())
        print()

        return df


# ── Save Helper ────────────────────────────────────────────────────────────────

    def _save(self, entry: dict):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        row = pd.DataFrame([[entry[c] for c in CSV_COLUMNS]], columns=CSV_COLUMNS)
        file_exists = os.path.isfile(self.data_path)
        row.to_csv(self.data_path, mode="a", index=False, header=not file_exists)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logger = StudyLogger()

    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        # python study_logger.py validate
        df = logger.validate_data()
        print(df[["timestamp", "mood", "agency", "metacognition",
                   "melatonin_taken", "phase"]].tail(10).to_string(index=False))
    else:
        # python study_logger.py  →  manual entry
        logger.manual_entry()
