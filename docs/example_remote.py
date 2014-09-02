import orangecontrib.remote as Orange
from orangecontrib.remote.classification.logistic_regression import LogisticRegressionLearner

iris = Orange.data.Table('iris')
print(iris)
print(iris[1])

logreg = LogisticRegressionLearner()(iris)
print(logreg(iris[1]))
