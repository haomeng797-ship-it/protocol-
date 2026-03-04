import pandas as pd
from datetime import datetime
import json
import os

class StudyLogger:
    def __init__(self, start_date_str="2026-02-18", protocol_path="../protocol/schedule.json"):
        self.start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        self.protocol_path = protocol_path
        self.data_path = "../data/raw_mood_data.csv"
        self.protocol = self._load_protocol()

    def _load_protocol(self):
        with open(self.protocol_path, 'r') as f:
            return json.load(f)

    def get_study_day(self):
        delta = datetime.now() - self.start_date
        return delta.days + 1

    def log_entry(self):
        day = self.get_study_day()
        assigned = self.protocol.get(str(day))
        
        print(f"--- N-of-1 Study: Day {day} ---")
        mood = input("Enter Mean Mood Score (0-100): ")
        
        # Fixing the logic bug: Capture both Assigned and Actual status
        print(f"Protocol Instruction: {'Take Melatonin' if assigned == 1 else 'Placebo'}")
        followed = input("Did you follow the protocol exactly? (y/n): ").lower()
        
        actual = assigned if followed == 'y' else (1 if assigned == 0 else 0)
        reason = "N/A" if followed == 'y' else input("Specify deviation reason: ")

        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "study_day": day,
            "mood_score": float(mood),
            "assigned_condition": int(assigned),
            "actual_intake": int(actual), # CRUCIAL: Fixed the missing variable
            "protocol_adherence": 1 if followed == 'y' else 0,
            "notes": reason
        }
        
        self._save_to_csv(entry)
        print("Data successfully committed to repository storage.")

    def _save_to_csv(self, entry):
        df = pd.DataFrame([entry])
        file_exists = os.path.isfile(self.data_path)
        df.to_csv(self.data_path, mode='a', index=False, header=not file_exists)

if __name__ == "__main__":
    logger = StudyLogger()
    logger.log_entry()
