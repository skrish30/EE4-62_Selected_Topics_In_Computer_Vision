clear all; close all; rng(1)
%% 0. Initialisation
init; clc;
%% 1. Generate data
vocab_size = 100;
[data_train, data_test] = getData(vocab_size);
%% 2. Random forest training
% choose tree options
forest_options = struct;
forest_options.depth = 10;
forest_options.numTrees = 1000;
forest_options.numSplits = 200;
forest_options.verbose = true; % outputs training update
forest_options.classifierId = 1;
forest_options.classifierCommitFirst = false;
forest_options.bagSizes = 100;
% standardise data to zero mean, unit variance  === DON'T DO THIS ===
%data_train = bsxfun(@rdivide, bsxfun(@minus, data_train, mean(data_train)), var(data_train) + 1e-10);
%data_test = bsxfun(@rdivide, bsxfun(@minus, data_test, mean(data_train)), var(data_train) + 1e-10);
true_class_vector = reshape((ones(10,15).*[1:10]')',[150,1]);
% train the forest
forest_model = forestTrain(data_train,true_class_vector,forest_options);
predicted_class_vector = forestTest(forest_model,data_test);
% results
results = sum(~logical(true_class_vector-predicted_class_vector))/length(true_class_vector)