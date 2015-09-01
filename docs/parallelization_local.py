import Orange
from Orange.classification import SVMLearner
from Orange.evaluation import TestOnTrainingData, AUC, CA

adult = Orange.data.Table('adult')
svm = SVMLearner()

results = [TestOnTrainingData(adult, [svm]) for i in range(3)]

for r in results:
    print(AUC(r), CA(r))
