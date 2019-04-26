import pandas as pd
import numpy as np
import os
import pickle
import pandas as pd
from tqdm import tqdm

import data_transform

def load_train():
    train = pickle.load(open('./data/train.p', 'rb'))
    return train


def load_transfrom_train(update=False):
    cache_path = './data/transform.p'
    existed = True
    if os.path.exists(cache_path):
        X_tr, y_tr = pickle.load(open(cache_path, 'rb'))
    else:
        existed = False
    
    if (not existed) or update:
        train = load_train()
        X_tr_new, y_tr_new = data_transform.transform_train(train)
        if existed:
            # upload cache
            X_tr_new = update_dataframe(X_tr, X_tr_new)

        dump = X_tr_new, y_tr_new
        pickle.dump(dump, open(cache_path, 'wb'))
        X_tr, y_tr = dump
    

    return X_tr, y_tr


def load_transfrom_test(update=False):
    cache_path = './data/test_transform.p'
    existed = True
    if os.path.exists(cache_path):
        result = pickle.load(open(cache_path, 'rb'))
    else:
        existed = False

    if (not existed) or update:
        raw = load_test()
        result_new = data_transform.transfrom_test(raw)
        if existed:
            # upload cache
            result_new = update_dataframe(result, result_new)
        pickle.dump(result_new, open(cache_path, 'wb'))
        result = result_new

    return result


def load_test():
    cache_path = './data/test_submission.p'
    test_path = './data/test'
    if os.path.exists(cache_path):
        result = pickle.load(open(cache_path, 'rb'))
    else:
        result = []
        for r, d, f in os.walk(test_path):
            for file in f:
                if file.endswith('.csv'):
                    name = file.split('.', 1)[0]
                    df = pd.read_csv(os.path.join(test_path, file), dtype={'acoustic_data': np.int16})
                    result.append((name, df['acoustic_data']))

        pickle.dump(result, open(cache_path, 'wb'))
    return result


def load_earthquake_id():
    cache_path = './data/earthquake_id.p'
    if os.path.exists(cache_path):
        earthquake_id = pickle.load(open(cache_path, 'rb'))
    else:
        train = load_train()
        earthquake_id = data_transform.transform_earthquake_id(train)
        pickle.dump(earthquake_id, open(cache_path, 'wb'))

    return earthquake_id


def update_dataframe(df_old, df_new):
    """ Update old dataframe with the new one, new values and new columns"""
    # assume left and right index matches
    df_old = df_old.reindex(columns=df_old.columns.union(df_new.columns))
    df_old.update(df_new)
    return df_old


def load_feature_names(version=None):
    """ load feature names, give newest by default"""
    feature_path = r'./data/features'
    feature_group = os.listdir(feature_path)

    feature_name, current_version = find_feature_version(feature_group, version)
    dump = []
    with open(os.path.join(feature_path, feature_name), 'r') as f:
        for line in f:
            dump.append(line.strip())
    return dump, current_version


def store_feature_names(column_names):
    """ Store feature names"""
    feature_path = r'./data/features'
    feature_group = os.listdir(feature_path)
    _, current_version = find_feature_version(feature_group)
    columns_names = sorted(column_names)
    with open(os.path.join(feature_path, f'{current_version + 1}_{len(column_names)}.txt'), 'w') as f:
        f.write('\n'.join(column_names))


def find_feature_version(feature_group, version=None):
    """ Return lastest file name and version number given names if version is None"""
    if not len(feature_group):
        return '', -1

    if version is None:
        feature_find = max(feature_group, key=lambda x: int(x.split('_', 1)[0]))
    else:
        version_find = [name for name in feature_group if name.split('_', 1)[0] == version]
        assert len(version_find) == 1, f'Too many versions: {version_find}'
        feature_find = version_find[0]

    current_version = int(feature_find.split('_', 1)[0])
    return feature_find, current_version

if __name__ == '__main__':
    X_tr, _ = load_transfrom_train(update=True)
    load_transfrom_test(update=True)
    store_feature_names(X_tr.columns.tolist())
    # print(load_feature_names()[-1])
    # column_names = ['a', 'b']
    # store_feature_names(column_names)
    # print(load_feature_names())