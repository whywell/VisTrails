from vistrails.core.modules.config import ModuleSettings
from vistrails.core.modules.vistrails_module import Module

import numpy as np
from sklearn import datasets
from sklearn.svm import LinearSVC as _LinearSVC
from sklearn.svm import SVC as _SVC
from sklearn.cross_validation import train_test_split, cross_val_score
from sklearn.metrics import SCORERS, roc_curve
from sklearn.grid_search import GridSearchCV as _GridSearchCV
from sklearn.preprocessing import StandardScaler as _StandardScaler
from sklearn.pipeline import make_pipeline


###############################################################################
# Example datasets

class Digits(Module):
    """Example dataset: digits.
    """
    _settings = ModuleSettings(namespace="datasets")
    _output_ports = [("data", "basic:List"),
                     ("target", "basic:List")]

    def compute(self):
        data = datasets.load_digits()
        self.set_output("data", data.data)
        self.set_output("target", data.target)


class Iris(Module):
    """Example dataset: iris.
    """
    _settings = ModuleSettings(namespace="datasets")
    _output_ports = [("data", "basic:List"),
                     ("target", "basic:List")]

    def compute(self):
        data = datasets.load_iris()
        self.set_output("data", data.data)
        self.set_output("target", data.target)


###############################################################################
# Base classes

class Estimator(Module):
    """Base class for all sklearn estimators.
    """
    _settings = ModuleSettings(abstract=True)
    _output_ports = [("model", "Estimator")]


class Predict(Module):
    """Apply a learned scikit-learn classifier model to test data.
    """
    # TODO : data depth=1
    _input_ports = [("classifier", "Estimator"),
                    ("data", "basic:List")]
    _output_ports = [("prediction", "basic:List"),
                     ("decision_function", "basic:List")]

    def compute(self):
        clf = self.get_input("classifier")
        data = self.get_input("data")
        predictions = clf.predict(data)
        decision_function = clf.decision_function(data)
        self.set_output("prediction", predictions)
        self.set_output("decision_function", decision_function)


class Transform(Module):
    """Apply a learned scikit-learn transformer to test data.
    """
    _input_ports = [("transformer", "Estimator"),
                    ("data", "basic:List")]
    _output_ports = [("transformed_data", "basic:List")]

    def compute(self):
        trans = self.get_input("transformer")
        data = self.get_input("data")
        transformed_data = trans.transform(data)
        self.set_output("transformed_data", transformed_data)


###############################################################################
# Cross-validation


class TrainTestSplit(Module):
    """Split data into training and testing randomly."""
    _settings = ModuleSettings(namespace="cross-validation")
    _input_ports = [("data", "basic:List"),
                    ("target", "basic:List"),
                    ("test_size", "basic:Float", {"defaults": [.25]})]
    _output_ports = [("training_data", "basic:List"),
                     ("training_target", "basic:List"),
                     ("test_data", "basic:List"),
                     ("test_target", "basic:List")]

    def compute(self):
        X_train, X_test, y_train, y_test = \
            train_test_split(self.get_input("data"), self.get_input("target"))
        self.set_output("training_data", X_train)
        self.set_output("training_target", y_train)
        self.set_output("test_data", X_test)
        self.set_output("test_target", y_test)


class CrossValScore(Module):
    """Split data into training and testing randomly."""
    _settings = ModuleSettings(namespace="cross-validation")
    _input_ports = [("model", "Estimator"),
                    ("data", "basic:List"),
                    ("target", "basic:List"),
                    ("metric", "basic:String", {"defaults": ["accuracy"]}),
                    ("folds", "basic:Integer", {"defaults": ["3"]})]
    _output_ports = [("scores", "basic:List")]

    def compute(self):
        model = self.get_input("model")
        data = self.get_input("data")
        target = self.get_input("target")
        metric = self.get_input("metric")
        folds = self.get_input("folds")
        scores = cross_val_score(model, data, target, scoring=metric, cv=folds)
        self.set_output("scores", scores)

###############################################################################
# Meta Estimators


class GridSearchCV(Estimator):
    """Perform cross-validated grid-search over a parameter grid."""
    _input_ports = [("model", "Estimator"),
                    ("data", "basic:List"),
                    ("target", "basic:List"),
                    ("metric", "basic:String", {"defaults": ["accuracy"]}),
                    ("folds", "basic:Integer", {"defaults": ["3"]}),
                    ("parameters", "basic:Dictionary")]
    _output_ports = [("scores", "basic:List"), ("model", "Estimator"),
                     ("best_parameters", "basic:Dictionary"),
                     ("best_score", "basic:Float")]

    def compute(self):
        base_model = self.get_input("model")
        grid = _GridSearchCV(base_model,
                             param_grid=self.get_input("parameters"),
                             cv=self.get_input("folds"),
                             scoring=self.get_input("metric"))
        if "data" in self.inputPorts:
            data = np.vstack(self.get_input("data"))
            target = self.get_input("target")
            grid.fit(data, target)
            self.set_output("scores", grid.grid_scores_)
            self.set_output("best_parameters", grid.best_params_)
            self.set_output("best_score", grid.best_score_)
        self.set_output("model", grid)


class Pipeline(Estimator):
    """Chain estimators to form a pipeline."""
    _input_ports = [("model1", "Estimator"),
                    ("model2", "Estimator", {'optional': True}),
                    ("model3", "Estimator", {'optional': True}),
                    ("model4", "Estimator", {'optional': True}),
                    ("train_data", "basic:List"),
                    ("train_target", "basic:List"),
                    ]

    def compute(self):
        models = ["model%d" % d for d in range(1, 5)]
        steps = [self.get_input(model) for model in models if model in self.inputPorts]
        pipeline = make_pipeline(*steps)
        if "train_data" in self.inputPorts:
            train_data = np.vstack(self.get_input("train_data"))
            train_classes = self.get_input("train_target")
            pipeline.fit(train_data, train_classes)
        self.set_output("model", pipeline)

###############################################################################
# Metrics


class Score(Module):
    """Compute a model performance metric."""
    _settings = ModuleSettings(namespace="metrics")
    _input_ports = [("model", "Estimator"),
                    ("data", "basic:List"),
                    ("target", "basic:List"),
                    ("metric", "basic:String", {"defaults": ["accuracy"]})]
    _output_ports = [("score", "basic:Float")]

    def compute(self):
        scorer = SCORERS[self.get_input("metric")]
        score = scorer(self.get_input("model"), self.get_input("data"), self.get_input("target"))
        self.set_output("score", score)


class ROCCurve(Module):
    """Compute a ROC curve."""
    _settings = ModuleSettings(namespace="metrics")
    _input_ports = [("model", "Estimator"),
                    ("data", "basic:List"),
                    ("target", "basic:List")]
    _output_ports = [("fpr", "basic:List"),
                     ("tpr", "basic:List")]

    def compute(self):
        model = self.get_input("model")
        data = self.get_input("data")
        if hasattr(model, "decision_function"):
            dec = model.decision_function(data)
        else:
            dec = model.predict_proba(data)[:, 1]
        fpr, tpr, _ = roc_curve(self.get_input("target"), dec)
        self.set_output("fpr", fpr)
        self.set_output("tpr", tpr)


###############################################################################<F2>
# Classifiers


class LinearSVC(Estimator):
    """Learns a linear support vector machine model from training data.
    """
    _settings = ModuleSettings(namespace="classifiers")
    _input_ports = [("train_data", "basic:List"),
                    ("train_classes", "basic:List"),
                    ("C", "basic:Float", {"defaults": [1]})]

    def compute(self):
        C = self.get_input("C")
        clf = _LinearSVC(C=C)
        if "train_data" in self.inputPorts:
            train_data = np.vstack(self.get_input("train_data"))
            train_classes = self.get_input("train_classes")
            clf.fit(train_data, train_classes)
        self.set_output("model", clf)


class SVC(Estimator):
    """Learns a linear support vector machine model from training data.
    """
    _settings = ModuleSettings(namespace="classifiers")
    _input_ports = [("train_data", "basic:List"),
                    ("train_classes", "basic:List"),
                    ("C", "basic:Float", {"defaults": [1]}),
                    ("gamma", "basic:Float", {"defaults": [0]})]

    def compute(self):
        C = self.get_input("C")
        gamma = self.get_input("gamma")
        clf = _SVC(C=C, gamma=gamma)
        if "train_data" in self.inputPorts:
            train_data = np.vstack(self.get_input("train_data"))
            train_classes = self.get_input("train_classes")
            clf.fit(train_data, train_classes)
        self.set_output("model", clf)


###############################################################################<F2>
# Preprocessing

class StandardScaler(Estimator):
    """Rescales data to have zero mean and unit variance per feature."""
    _settings = ModuleSettings(namespace="preprocessing")
    _input_ports = [("train_data", "basic:List")]

    def compute(self):
        trans = _StandardScaler()
        if "train_data" in self.inputPorts:
            train_data = np.vstack(self.get_input("train_data"))
            trans.fit(train_data)
        self.set_output("model", trans)

_modules = [Digits, Iris, Estimator, Predict, Transform,
            LinearSVC, SVC, TrainTestSplit, Score, ROCCurve, CrossValScore,
            GridSearchCV, StandardScaler, Pipeline]