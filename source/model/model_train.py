from abc import ABCMeta, abstractmethod
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error
import datetime
import os.path
import pickle
import json
import joblib

import data_loader

class ModelTrain(metaclass=ABCMeta):

    subclasses = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.subclasses.append(cls)
    
    def __init__(self, feature_version=None, params=None, logger=None):
        self.params = params
        self.logger = logger
        if feature_version == 'stack':
            self.feature_version = feature_version
        else:
            self.columns, self.feature_version = data_loader.load_feature_names(feature_version)
        self.model_name = type(self).__name__
        self.model_pack = []
        self.fold_choice = None
        self.prediction_dump = []

    def update(self, params):
        self.params.update(params)

    @abstractmethod
    def train(self, X_train, y_train, X_valid, y_valid):
        pass
    
    @property
    def save_name(self):
        prefix = datetime.datetime.now().strftime(r'%m%d_%H%M')
        name_model = f'{prefix}_{self.model_name}_{self.feature_version}_CV_{self.oof_score:.2f}_{self.mean_score:.2f}_{self.std_score:.2f}_{self.fold_choice}'
        return name_model
    
    def store_model(self):
        """ Save model for each fold and overall oof """
        joblib.dump((self.model_pack, self.oof), os.path.join('./data/transfer', self.save_name + '.p'))
    
    def store_prediction(self):
        name_model = self.save_name

        data = {}
        data['prediction'] = self.prediction
        data['oof'] = self.oof
        data['prediction_dump'] = self.prediction_dump

        pickle.dump(data, open(os.path.join('./data/prediction', name_model), 'wb'))
        
        params = {}
        params['feature_version'] = self.feature_version
        params['params'] = self.params
        
        with open(os.path.join('./data/params', name_model), 'w') as f:
            json.dump(params, f, indent=4, sort_keys=True)

        self.logger.info('Model stored!')
    
    def train_CV(self, X, y, fold_iter):
        dump = []
        oof = np.zeros(len(y))
        divisor = np.zeros(len(y))

        fold_iter, self.fold_choice = fold_iter
        for fold_n, (train_index, valid_index) in enumerate(fold_iter):
            X_train, X_valid = X.iloc[train_index], X.iloc[valid_index]
            y_train, y_valid = y.iloc[train_index], y.iloc[valid_index]

            predictor, model = self.train(X_train, y_train, X_valid, y_valid)
            y_pred = predictor(X_valid)

            oof[valid_index] += y_pred.flatten()
            divisor[valid_index] += 1

            score = mean_absolute_error(y_pred, y_valid)
            dump.append(score)
            self.logger.info(f"fold: {fold_n}, score: {score:.2f}")

        oof = oof / divisor # average

        # store all necessary info
        self.mean_score = np.mean(dump)
        self.std_score = np.std(dump)
        self.oof = oof
        self.oof_score = mean_absolute_error(oof, y)

        self.logger.info(f"oof_score: {self.oof_score:.2f}, mean_score: {self.mean_score:.2f}, std: {self.std_score:.2f}")
        return self.oof_score, self.mean_score, self.std_score, dump


    def train_CV_test(self, X, y, X_test, fold_iter, exclude_score=10):
        """ Return predicted values as well as oof"""
        dump = []
        prediction = np.zeros(len(X_test))
        oof = np.zeros(len(y))
        divisor = np.zeros(len(y))

        if self.feature_version != 'stack':
            X = X[self.columns]
            X_test = X_test[self.columns]
        
        exclude_count = 0
        fold_iter, self.fold_choice = fold_iter
        for fold_n, (train_index, valid_index) in enumerate(fold_iter):
            X_train, X_valid = X.iloc[train_index], X.iloc[valid_index]
            y_train, y_valid = y.iloc[train_index], y.iloc[valid_index]

            predictor, model = self.train(X_train, y_train, X_valid, y_valid)
            y_pred = predictor(X_valid)

            oof[valid_index] += y_pred.flatten()
            divisor[valid_index] += 1

            score = mean_absolute_error(y_pred, y_valid)
            dump.append(score)
            self.model_pack.append((model, score))

            self.logger.info(f"fold: {fold_n}, score: {score:.2f}")

            if score > exclude_score:
                self.logger.warning(f"Excluded as the cutoff: {exclude_score}, fold: {fold_n}, score: {score:.2f}")
                exclude_count += 1
            else:
                tmp = predictor(X_test).flatten()
                prediction += tmp
                self.prediction_dump.append((score, tmp))

        oof /= divisor # average

        # store all necessary info
        self.mean_score = np.mean(dump)
        self.std_score = np.std(dump)
        self.prediction = prediction / (fold_n - exclude_count)
        self.oof = oof
        self.oof_score = mean_absolute_error(oof, y)

        self.logger.info(f"oof_score: {self.oof_score:.2f}, mean_score: {self.mean_score:.2f}, std: {self.std_score:.2f}")
        return self.prediction, self.oof