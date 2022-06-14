import pandas as pd
from biclustlib.benchmark.data import load_tavazoie, load_prelic, load_jaskowiak
from sklearn.preprocessing import KBinsDiscretizer
from setuptools import setup, find_packages

# setup(name='bcl_web', version='1.0', packages=find_packages())

# обертка для датафрейма для удобства представления в виде списка
class Dataset:
    all = []

    def __init__(self, name: str, data: pd.DataFrame):
        self.name = name
        self.data = data
        Dataset.all.append(self)

    def __str__(self):
        return self.name


# функция для дискретизации данных
# (представления дробных значений в виде целых с помощью разделения на корзины)
def discretize_data(raw_data: pd.DataFrame, n_bins: int = 2) -> pd.DataFrame:
    return pd.DataFrame(
        KBinsDiscretizer(n_bins, encode='ordinal', strategy='kmeans').fit_transform(raw_data),
        index=raw_data.index).astype(int if n_bins > 2 else bool)


# списки графиков и таблиц с метриками
graphics = [
    "Average Spearman Rho",
    "Mean Squared Residue",
    "Scaling Mean Squared Residue",
    "Virtual Error",
    "Virtual Error transposed",
    "execution time",
    "biclusters found",
]
tables = [
    "Average Spearman Rho",
    "Mean Squared Residue",
    "Scaling Mean Squared Residue",
    "Virtual Error",
    "Virtual Error transposed",
    "general report",
]
links = [
    "biclustering/report/metrics/ASR.png",
    "biclustering/report/metrics/MSR.png",
    "biclustering/report/metrics/SMSR.png",
    "biclustering/report/metrics/VE.png",
    "biclustering/report/metrics/VEt.png",
    "biclustering/report/times.png",
    "biclustering/report/found.png",
]

# загрузка встроенных в библиотеку датасетов
Dataset("Tavazoie", load_tavazoie())
Dataset("Prelic", load_prelic())

data_list = load_jaskowiak()
name_list = [
    "Alpha Factor",
    "CDC 15",
    "CDC 28",
    "Elutriation",
    "1mM Menadione",
    "1M Sorbitol",
    "15mM Diamide",
    "25mM DTT",
    "Constant 32 nM H2O2",
    "Diauxic Shift",
    "Complete DTT",
    "Heat Shock 1",
    "Heat Shock 2",
    "Nitrogen Depletion",
    "YPD 1",
    "YPD 2",
    "Yeast Sporulation"
]
if len(data_list) == len(name_list):
    for i in range(len(data_list)):
        Dataset("Jaskowiak: " + name_list[i], data_list[i])
else:
    raise ImportError
