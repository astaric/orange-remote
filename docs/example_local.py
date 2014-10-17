import Orange
from Orange.classification.logistic_regression import LogisticRegressionLearner

iris = Orange.data.Table('iris')
logreg = LogisticRegressionLearner()(iris)
print(logreg(iris[0]))
