import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, mean_squared_error, r2_score
import joblib
import os


class StudentPerformancePredictor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.pass_fail_model = None
        self.grade_model = None
        self.at_risk_model = None
        self.score_model = None
        self.feature_cols = [
            'attendance', 'test1', 'test2', 'test3',
            'assignment1', 'assignment2', 'assignment3',
            'exam_score', 'avg_test', 'avg_assignment'
        ]

    # ─────────────────────────────────────────────
    # Grading — scheme-aware
    # ─────────────────────────────────────────────
    @staticmethod
    def calculate_final_score(exam, avg_test, avg_assignment, attendance, scheme=None):
        if scheme:
            w = scheme.get("weights", {})
            we, wt, wa, watt = (w.get("exam",60), w.get("tests",20),
                                w.get("assignments",10), w.get("attendance",10))
        else:
            we, wt, wa, watt = 60, 20, 10, 10
        score = (exam*(we/100) + avg_test*(wt/100) +
                 avg_assignment*(wa/100) + attendance*(watt/100))
        return round(float(np.clip(score, 0, 100)), 2)

    @staticmethod
    def score_to_grade(score, scheme=None):
        gb = scheme.get("grade_boundaries", {}) if scheme else {}
        a  = gb.get("A", 70); b = gb.get("B", 60)
        c  = gb.get("C", 50); d = gb.get("D", 45)
        if score >= a: return 'A'
        if score >= b: return 'B'
        if score >= c: return 'C'
        if score >= d: return 'D'
        return 'F'

    @staticmethod
    def grade_to_int(score, scheme=None):
        gb = scheme.get("grade_boundaries", {}) if scheme else {}
        a  = gb.get("A", 70); b = gb.get("B", 60)
        c  = gb.get("C", 50); d = gb.get("D", 45)
        if score >= a: return 4
        if score >= b: return 3
        if score >= c: return 2
        if score >= d: return 1
        return 0

    # ─────────────────────────────────────────────
    # Dataset Generation
    # ─────────────────────────────────────────────
    def generate_dataset(self, n_samples=500):
        np.random.seed(42)
        n = n_samples

        def mix(a_params, b_params, c_params, ratios):
            na, nb, nc = [int(n * r) for r in ratios]
            na = n - nb - nc  # ensure total = n
            return np.concatenate([
                np.random.beta(*a_params, na) * 100,
                np.random.beta(*b_params, nb) * 100,
                np.random.beta(*c_params, nc) * 100
            ])

        attendance   = mix((8,2),(4,4),(2,6), (0.6,0.3,0.1))
        test1        = mix((7,2),(4,4),(2,5), (0.5,0.3,0.2))
        test2        = mix((7,2),(4,4),(2,5), (0.5,0.3,0.2))
        test3        = mix((7,2),(4,4),(2,5), (0.5,0.3,0.2))
        assignment1  = mix((7,2),(4,4),(2,5), (0.6,0.25,0.15))
        assignment2  = mix((7,2),(4,4),(2,5), (0.6,0.25,0.15))
        assignment3  = mix((7,2),(4,4),(2,5), (0.6,0.25,0.15))
        exam_score   = mix((7,2),(4,4),(2,5), (0.5,0.3,0.2))

        for arr in [attendance, test1, test2, test3,
                    assignment1, assignment2, assignment3, exam_score]:
            np.random.shuffle(arr)

        avg_test       = (test1 + test2 + test3) / 3
        avg_assignment = (assignment1 + assignment2 + assignment3) / 3

        final_score = np.array([
            self.calculate_final_score(e, at, aa, att)
            for e, at, aa, att in zip(exam_score, avg_test, avg_assignment, attendance)
        ])

        df = pd.DataFrame({
            'attendance':   np.round(attendance,   2),
            'test1':        np.round(test1,        2),
            'test2':        np.round(test2,        2),
            'test3':        np.round(test3,        2),
            'assignment1':  np.round(assignment1,  2),
            'assignment2':  np.round(assignment2,  2),
            'assignment3':  np.round(assignment3,  2),
            'exam_score':   np.round(exam_score,   2),
            'avg_test':     np.round(avg_test,     2),
            'avg_assignment': np.round(avg_assignment, 2),
            'final_score':  final_score,
        })

        df['pass_fail']      = (df['final_score'] >= 45).astype(int)
        df['grade_category'] = df['final_score'].apply(self.grade_to_int)
        df['at_risk']        = (
            (df['final_score']   < 50) |
            (df['exam_score']    < 40) |
            (df['attendance']    < 70) |
            (df['avg_test']      < 40) |
            (df['avg_assignment']< 40)
        ).astype(int)

        return df

    # ─────────────────────────────────────────────
    # Training
    # ─────────────────────────────────────────────
    def train_models(self, df):
        print("Preparing data...")
        X       = df[self.feature_cols]
        X_scaled = self.scaler.fit_transform(X)

        X_tr, X_te, y_pf_tr, y_pf_te = train_test_split(
            X_scaled, df['pass_fail'], test_size=0.2, random_state=42, stratify=df['pass_fail'])

        _, _, y_gc_tr, y_gc_te = train_test_split(
            X_scaled, df['grade_category'], test_size=0.2, random_state=42, stratify=df['grade_category'])

        _, _, y_ar_tr, y_ar_te = train_test_split(
            X_scaled, df['at_risk'], test_size=0.2, random_state=42, stratify=df['at_risk'])

        _, _, y_sc_tr, y_sc_te = train_test_split(
            X_scaled, df['final_score'], test_size=0.2, random_state=42)

        # Pass/Fail
        print("\nTraining Pass/Fail Model...")
        self.pass_fail_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.pass_fail_model.fit(X_tr, y_pf_tr)
        pf_pred = self.pass_fail_model.predict(X_te)
        pf_acc  = accuracy_score(y_pf_te, pf_pred)
        print(f"Accuracy: {pf_acc:.4f}")
        if len(np.unique(y_pf_te)) > 1:
            print(classification_report(y_pf_te, pf_pred, target_names=['Fail','Pass']))

        # Grade Category
        print("\nTraining Grade Category Model...")
        self.grade_model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        self.grade_model.fit(X_tr, y_gc_tr)
        gc_pred = self.grade_model.predict(X_te)
        gc_acc  = accuracy_score(y_gc_te, gc_pred)
        print(f"Accuracy: {gc_acc:.4f}")

        # At-Risk
        print("\nTraining At-Risk Model...")
        self.at_risk_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.at_risk_model.fit(X_tr, y_ar_tr)
        ar_pred = self.at_risk_model.predict(X_te)
        ar_acc  = accuracy_score(y_ar_te, ar_pred)
        print(f"Accuracy: {ar_acc:.4f}")
        if len(np.unique(y_ar_te)) > 1:
            print(classification_report(y_ar_te, ar_pred, target_names=['Not At Risk','At Risk']))

        # Score Regression
        print("\nTraining Score Prediction Model...")
        self.score_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.score_model.fit(X_tr, y_sc_tr)
        sc_pred = self.score_model.predict(X_te)
        mse = mean_squared_error(y_sc_te, sc_pred)
        r2  = r2_score(y_sc_te, sc_pred)
        print(f"MSE: {mse:.4f}  |  R²: {r2:.4f}")

        return {
            'pass_fail_accuracy':     round(pf_acc * 100, 2),
            'grade_accuracy':         round(gc_acc * 100, 2),
            'at_risk_accuracy':       round(ar_acc * 100, 2),
            'score_r2':               round(r2 * 100, 2),
            'score_mse':              round(mse, 4),
        }

    # ─────────────────────────────────────────────
    # Prediction
    # ─────────────────────────────────────────────
    def predict_student(self, row: dict, scheme: dict = None) -> dict:
        nt = scheme.get("num_tests", 3)       if scheme else 3
        na = scheme.get("num_assignments", 3) if scheme else 3

        test_scores  = [float(row.get(f"test{i+1}", 0))       for i in range(nt)]
        asgn_scores  = [float(row.get(f"assignment{i+1}", 0)) for i in range(na)]
        avg_test       = sum(test_scores)  / len(test_scores)  if test_scores  else 0
        avg_assignment = sum(asgn_scores)  / len(asgn_scores)  if asgn_scores  else 0
        final_score    = self.calculate_final_score(
            row['exam_score'], avg_test, avg_assignment, row['attendance'], scheme)

        features = pd.DataFrame([{
            'attendance':     row['attendance'],
            'test1':          row['test1'],
            'test2':          row['test2'],
            'test3':          row['test3'],
            'assignment1':    row['assignment1'],
            'assignment2':    row['assignment2'],
            'assignment3':    row['assignment3'],
            'exam_score':     row['exam_score'],
            'avg_test':       avg_test,
            'avg_assignment': avg_assignment,
        }])

        X_scaled = self.scaler.transform(features)

        pf_proba    = self.pass_fail_model.predict_proba(X_scaled)[0]
        gc_pred     = self.grade_model.predict(X_scaled)[0]
        gc_proba    = self.grade_model.predict_proba(X_scaled)[0]
        ar_proba    = self.at_risk_model.predict_proba(X_scaled)[0]
        pred_score  = float(self.score_model.predict(X_scaled)[0])

        pass_mark = scheme.get("pass_mark", 45) if scheme else 45
        grade     = self.score_to_grade(final_score, scheme)
        is_pass   = final_score >= pass_mark
        is_at_risk = (
            final_score    < pass_mark + 5 or
            row['exam_score']      < 40 or
            row['attendance']      < 70 or
            avg_test       < 40 or
            avg_assignment < 40
        )

        risk_factors = []
        if row['exam_score']    < 40: risk_factors.append('Poor Exam Performance')
        if avg_test      < 40:        risk_factors.append('Poor Test Performance')
        if row['attendance']    < 70: risk_factors.append('Low Attendance')
        if avg_assignment < 40:       risk_factors.append('Low Assignment Scores')

        return {
            'avg_test':          round(avg_test, 2),
            'avg_assignment':    round(avg_assignment, 2),
            'final_score':       final_score,
            'predicted_score':   round(pred_score, 2),
            'pass_fail':         'Pass' if is_pass else 'Fail',
            'pass_probability':  round(float(pf_proba[1]) * 100, 2),
            'grade_category':    grade,
            'grade_confidence':  round(float(gc_proba[gc_pred]) * 100, 2),
            'at_risk':           'Yes' if is_at_risk else 'No',
            'risk_probability':  round(float(ar_proba[1]) * 100, 2),
            'risk_factors':      risk_factors,
        }

    # ─────────────────────────────────────────────
    # Save / Load
    # ─────────────────────────────────────────────
    def save_models(self, path='models/'):
        os.makedirs(path, exist_ok=True)
        joblib.dump(self.scaler,          f'{path}scaler.pkl')
        joblib.dump(self.pass_fail_model, f'{path}pass_fail_model.pkl')
        joblib.dump(self.grade_model,     f'{path}grade_model.pkl')
        joblib.dump(self.at_risk_model,   f'{path}at_risk_model.pkl')
        joblib.dump(self.score_model,     f'{path}score_model.pkl')
        print(f"Models saved to {path}")

    def load_models(self, path='models/'):
        self.scaler          = joblib.load(f'{path}scaler.pkl')
        self.pass_fail_model = joblib.load(f'{path}pass_fail_model.pkl')
        self.grade_model     = joblib.load(f'{path}grade_model.pkl')
        self.at_risk_model   = joblib.load(f'{path}at_risk_model.pkl')
        self.score_model     = joblib.load(f'{path}score_model.pkl')
        print(f"Models loaded from {path}")

    def models_exist(self, path='models/'):
        files = ['scaler.pkl','pass_fail_model.pkl','grade_model.pkl',
                 'at_risk_model.pkl','score_model.pkl']
        return all(os.path.exists(f'{path}{f}') for f in files)


# ─────────────────────────────────────────────
# Entry point – run directly to train & save
# ─────────────────────────────────────────────
if __name__ == '__main__':
    predictor = StudentPerformancePredictor()
    print("Generating dataset...")
    df = predictor.generate_dataset(500)
    print(f"Dataset shape: {df.shape}")
    print(df.head())
    print("\n" + "="*50)
    predictor.train_models(df)
    predictor.save_models()
    print("\nDone! Models ready.")