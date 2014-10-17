from orangecontrib import remote
with remote.server('127.0.0.1:9465'):
    import Orange
    from Orange.classification.logistic_regression import LogisticRegressionLearner

iris = Orange.data.Table('iris')
logreg = LogisticRegressionLearner()(iris)
print(logreg(iris[0]))
