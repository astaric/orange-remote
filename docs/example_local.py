import Orange
from Orange.classification import LogisticRegressionLearner
from Orange.evaluation import CrossValidation, AUC, CA

iris = Orange.data.Table('iris')
logreg = LogisticRegressionLearner()

results = CrossValidation(iris, [logreg])
print(AUC(results), CA(results))
