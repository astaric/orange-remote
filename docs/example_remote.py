from orangecontrib import remote
with remote.server('127.0.0.1:9465'):
    import Orange
    from Orange.classification import LogisticRegressionLearner
    from Orange.evaluation import CrossValidation, AUC, CA

iris = Orange.data.Table('iris')
logreg = LogisticRegressionLearner()

results = CrossValidation(iris, [logreg])
print(AUC(results), CA(results))
