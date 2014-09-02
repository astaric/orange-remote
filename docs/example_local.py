import Orange
from Orange.classification.logistic_regression import LogisticRegressionLearner

iris = Orange.data.Table('iris')
print(iris)
print(iris[1])

logreg = LogisticRegressionLearner()(iris)
print(logreg(iris[1]))
