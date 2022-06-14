import multiprocessing

import matplotlib
from biclustlib.algorithms import ChengChurchAlgorithm, BitPatternBiclusteringAlgorithm, LargeAverageSubmatrices
from biclustlib.algorithms.wrappers import RConservedGeneExpressionMotifs, \
    RBinaryInclusionMaximalBiclusteringAlgorithm, RPlaid, Spectral
from biclustlib.benchmark import Algorithm, GeneExpressionBenchmark
from django.http import HttpResponse
from django.template import loader
from .preprocessing import *
import os
import platform
import shutil

matplotlib.use('Agg')  # оптимизация рисования графиков


# view основной страницы,
# получает списки датасетов, графиков, таблиц
# и платформу (для ограничения работы анти-виндовских алгоритмов)
def main_view(request):
    template = loader.get_template('biclustering/main.html')
    disabled_by_os = False
    if platform.system() == 'Windows':
        disabled_by_os = True
    context = {
        "datasets": Dataset.all,
        "graphics": graphics,
        "tables": tables,
        "disabled_by_os": disabled_by_os
    }
    return HttpResponse(template.render(context, request))


# view страницы результатов,
# здесь происходит вся обработка параметров и запуск алгоритмов
def run_view(request):
    try:
        template = loader.get_template('biclustering/run.html')

        # получение датасетов из списка или файла
        params = request.GET
        data = pd.DataFrame()
        if params.get("dataset") == "select":
            data = Dataset.all[int(params.get("dataset_dropdown"))].data
        elif params.get("dataset") == "upload":
            if params.get("dataset_file") != "":
                data = pd.read_csv(params.get("dataset_file"))
            else:
                raise FileNotFoundError

        # обработка параметров особого формата:
        # булевских полей и полей, которые могут принимать значения разного типа
        LAS_scale_data = True if params.get("LAS_scale_data") else False
        LAS_transform = True if params.get("LAS_transform") else False
        Plaid_fit_background_layer = True if params.get("Plaid_fit_background_layer") else False
        Spectral_n_svd_vecs = None if params.get("Spectral_n_svd_vecs") == '' \
            else int(params.get("Spectral_n_svd_vecs"))
        Spectral_random_state = None if params.get("Spectral_random_state") == '' \
            else int(params.get("Spectral_random_state"))
        CCA_msr_threshold = 'estimate' if params.get("CCA_msr_threshold") == 'estimate' \
            else float(params.get("CCA_msr_threshold"))

        # дискретизация данных
        # необходима для некоторых алгоритмов
        data_dis = discretize_data(data, int(params.get("discretion_level")))
        data_bin = discretize_data(data)

        # добавление алгоритмов в список исполняемых в зависимости от галочек интерфейса,
        # подстановка аргументов также в зависимости от параметров из интерфейса
        algo_setup = []
        if params.get("CCA"):
            algo_setup.append(Algorithm('CCA', ChengChurchAlgorithm(
                int(params.get("CCA_num_biclusters")),
                CCA_msr_threshold,
                float(params.get("CCA_multiple_node_deletion_threshold")),
                int(params.get("CCA_data_min_cols")),
            ), data))
        if params.get("xMotifs"):
            algo_setup.append(Algorithm('xMotifs', RConservedGeneExpressionMotifs(
                int(params.get("xMotifs_num_biclusters")),
                int(params.get("xMotifs_num_seeds")),
                int(params.get("xMotifs_num_sets")),
                int(params.get("xMotifs_set_size")),
                float(params.get("xMotifs_alpha")),
            ), data_dis))
        if params.get("BiBit"):
            algo_setup.append(Algorithm('BiBit', BitPatternBiclusteringAlgorithm(
                int(params.get("BiBit_min_rows")),
                int(params.get("BiBit_min_cols")),
            ), data_bin))
        if params.get("Bimax"):
            algo_setup.append(Algorithm('Bimax', RBinaryInclusionMaximalBiclusteringAlgorithm(
                int(params.get("Bimax_num_biclusters")),
                int(params.get("Bimax_min_rows")),
                int(params.get("Bimax_min_cols")),
            ), data_bin))
        if params.get("LAS"):
            algo_setup.append(Algorithm('LAS', LargeAverageSubmatrices(
                int(params.get("LAS_num_biclusters")),
                float(params.get("LAS_score_threshold")),
                int(params.get("LAS_randomized_searches")),
                LAS_scale_data,
                LAS_transform,
            ), data))
        if params.get("Plaid"):
            algo_setup.append(Algorithm('Plaid', RPlaid(
                int(params.get("Plaid_num_biclusters")),
                Plaid_fit_background_layer,
                float(params.get("Plaid_row_prunning_threshold")),
                float(params.get("Plaid_col_prunning_threshold")),
                int(params.get("Plaid_significance_tests")),
                int(params.get("Plaid_back_fitting_steps")),
                int(params.get("Plaid_initialization_iterations")),
                int(params.get("Plaid_iterations_per_layer")),
            ), data))
        if params.get("Spectral"):
            algo_setup.append(Algorithm('Spectral', Spectral(**{
                "n_clusters": int(params.get("Spectral_n_clusters")),
                "method": params.get("Spectral_method"),
                "n_components": int(params.get("Spectral_n_components")),
                "n_best": int(params.get("Spectral_n_best")),
                "svd_method": params.get("Spectral_svd_method"),
                "n_svd_vecs": Spectral_n_svd_vecs,
                "mini_batch": params.get("Spectral_mini_batch"),
                "init": params.get("Spectral_init"),
                "n_init": int(params.get("Spectral_n_init")),
                "random_state": Spectral_random_state,
            }), data + abs(data.min().min()) + 1))

        # проверка на пустой исполняемый список
        if not len(algo_setup):
            raise NotImplementedError

        # включаем мультипроцессинг, если необходимо
        pool = None
        if params.get("multiprocessing"):
            pool = multiprocessing.Pool()
        # формируем из алгоритмов бенчмарк и запускаем
        benchmark = GeneExpressionBenchmark(algorithms=algo_setup,
                                            raw_data=data,
                                            reduction_level=int(params.get("reduction_level"))).run(pool)
        # очищаем папку из-под предыдущего репорта и генерируем новый
        script_dir = os.path.dirname(os.path.realpath('__file__'))
        rel_path = r"biclustering\static\biclustering\report"
        if os.path.exists(os.path.join(script_dir, rel_path)):
            shutil.rmtree(os.path.join(script_dir, rel_path))
        benchmark.generate_report(os.path.join(script_dir, rel_path))
        # запускаем анализ обогащения, если необходимо
        if params.get("graphic_goea") or params.get("table_goea"):
            benchmark.perform_goea()
            benchmark.generate_goea_report(os.path.join(script_dir, rel_path))

        if params.get("multiprocessing"):
            pool.close()

        # формируем списки графиков и таблиц для вывода согласно галочкам
        context = {
            "graphics": [],
            "tables": [],
            "from": "gene_expression"
        }
        for i in range(max(len(graphics), len(tables))):
            if params.get("graphic_" + str(i)):
                context["graphics"].append(links[i])
            if params.get("table_" + str(i)):
                context["tables"].append(tables[i])
        if params.get("graphic_goea"):
            context["graphics"].append("biclustering/report/goea.png")
        if params.get("table_goea"):
            context["tables"].append("GOEA report")

        return HttpResponse(template.render(context, request))
    # отлавливаем вероятные пользовательские ошибки:
    except FileNotFoundError:
        return error_view(request, "Please upload necessary file.")  # скорее всего не прикрепили датасет
    # except NotImplementedError:
    #     return error_view(request, "Please select at least one algorithm to run.") # не выбраны алгоритмы
    # except ValueError, TypeError:
    #     return error_view(request, 'You might have entered incorrect parameters.') # неверный тип параметров
    # except:
    #     return error_view(request, "Something went wrong, please try again.") # и что угодно непредвиденное


def save_view(request):
    # создаем архив из репорта и выдаем его на сохранение пользователю
    script_dir = os.path.dirname(os.path.realpath('__file__'))
    rel_path = r"biclustering\static\biclustering\report"
    filename = r"biclustering\static\biclustering\report.zip"

    shutil.make_archive(os.path.join(script_dir, rel_path),
                        'zip',
                        os.path.join(script_dir, rel_path))
    fileopen = open(os.path.join(script_dir, filename), "rb")
    response = HttpResponse(fileopen.read(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename={0}'.format("report.zip")
    fileopen.close()
    return response


# окошко отображения ошибок
def error_view(request, message):
    template = loader.get_template('biclustering/error.html')
    context = {
        "message": message,
    }
    return HttpResponse(template.render(context, request))


# странички для таблиц, выбираются согласно пришедшему номеру в списке
def table(request, num):
    table_links = [
        'detailed_metrics/ASR.csv',
        'detailed_metrics/MSR.csv',
        'detailed_metrics/SMSR.csv',
        'detailed_metrics/VE.csv',
        'detailed_metrics/VEt.csv',
        'report.csv',
        'goea_report.csv',
    ]
    data = pd.read_csv('biclustering/static/biclustering/report/' + table_links[num])
    return HttpResponse(data.to_html())
