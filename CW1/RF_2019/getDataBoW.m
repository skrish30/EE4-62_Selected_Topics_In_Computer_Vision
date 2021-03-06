clear all; close all; 
warning('off','all');
init;clc;
rng(1)
showImg = 0; % Show training & testing images and their image feature vector (histogram representation)
PHOW_Sizes = [4 8 10]; % Multi-resolution, these values determine the scale of each layer.
PHOW_Step = 8; % The lower the denser. Select from {2,4,8,16}
imgSel = [15 15]; % randomly select 15 images each class without replacement. (For both training & testing)
folderName = './Caltech_101/101_ObjectCategories';
classList = dir(folderName);
classList = {classList(3:end).name}; % 10 classes
% Load Images -> Description (Dense SIFT)
disp('Loading training images...')
cnt = 1;
if showImg
    figure('Units','normalized','Position',[.05 .1 .4 .9]);
    suptitle('Training image samples');
end
for c = 1:length(classList)
    subFolderName = fullfile(folderName,classList{c});
    imgList = dir(fullfile(subFolderName,'*.jpg'));
    imgIdx{c} = randperm(length(imgList));
    imgIdx_tr = imgIdx{c}(1:imgSel(1));
    imgIdx_te = imgIdx{c}(imgSel(1)+1:sum(imgSel));
    for i = 1:length(imgIdx_tr)
        I = imread(fullfile(subFolderName,imgList(imgIdx_tr(i)).name));
        % Visualise
        if i < 6 & showImg
            subaxis(length(classList),5,cnt,'SpacingVert',0,'MR',0);
            imshow(I);
            cnt = cnt+1;
            drawnow;
        end
        if size(I,3) == 3
            I = rgb2gray(I); % PHOW work on gray scale image
        end
        % For details of image description, see http://www.vlfeat.org/matlab/vl_phow.html
        [~, desc_tr{c,i}] = vl_phow(single(I),'Sizes',PHOW_Sizes,'Step',PHOW_Step); %  extracts PHOW features (multi-scaled Dense SIFT)
    end
end
% Load Images -> Description (Dense SIFT)
% disp('Processing testing images...');
cnt = 1;
        for c = 1:length(classList)
            subFolderName = fullfile(folderName,classList{c});
            imgList = dir(fullfile(subFolderName,'*.jpg'));
            imgIdx_te = imgIdx{c}(imgSel(1)+1:sum(imgSel));
            for i = 1:length(imgIdx_te)
                I = imread(fullfile(subFolderName,imgList(imgIdx_te(i)).name));
                % Visualise
                if i < 6 & showImg
                    subaxis(length(classList),5,cnt,'SpacingVert',0,'MR',0);
                    imshow(I);
                    cnt = cnt+1;
                    drawnow;
                end
                if size(I,3) == 3
                    I = rgb2gray(I);
                end
                [~, desc_te{c,i}] = vl_phow(single(I),'Sizes',PHOW_Sizes,'Step',PHOW_Step);
            end
        end
% Build visual vocabulary (codebook) for 'Bag-of-Words method'
disp('Building visual codebook...')
% single -> double

%%
[desc_sel,~] = double(vl_colsubset(cat(2,desc_tr{:}), 10e4)); % Randomly select 100k SIFT descriptors for clustering
% K-means clustering
no_kmeans_initialisations = 10;
max_iterations = 0;%[5,10,50,100];
vocab_sizes = [5,10,20,50,100,200,500,1000,2000,5000];
results_store = zeros(3,no_kmeans_initialisations,length(vocab_sizes),length(max_iterations)); % [knn, svm],[no kmeans inits],[vocab_sizes]
time_store = zeros(2,no_kmeans_initialisations,length(vocab_sizes),length(max_iterations)); % [t_kmeans, t_quantisation], ...
vocab_idx = 1;
for vocab_size = vocab_sizes
    iter_idx = 1;
    for max_iter = max_iterations
        for kmeans_init = 1:no_kmeans_initialisations
            disp(['Loop: vocab_size = ',num2str(vocab_size),', max_iter = ',num2str(max_iter),', kmeans_init = ',num2str(kmeans_init)])
            tic % start timer for k-means
            %[~, words] = kmeans(desc_sel', vocab_size, 'MaxIter', max_iter);
            [~, words, ~] = kmeans2(desc_sel, kseeds(desc_sel,vocab_size));words = words';
            elapsed_time = toc; % stop timer for k-means
            time_store(1,kmeans_init,vocab_idx,iter_idx) = elapsed_time;
            % disp('Encoding Training Images...')
            bags_of_words_training = zeros(vocab_size,150); % 150 = 10 classes * 15 images per class
            bags_of_words_testing = zeros(vocab_size,150);
            imTrack = 1;
            tic % start timer for training & test image quantisation
            % Vector Quantisation (training images)
            for class = 1:10
                for image = 1:15
                    image_descriptors = desc_tr(class,image);
                    image_descriptors = image_descriptors{1};
                    closest_words = knnsearch(words,image_descriptors');
                    for k = 1:length(closest_words)
                        bags_of_words_training(closest_words(k),imTrack) = bags_of_words_training(closest_words(k),imTrack) + 1;
                    end
                    bags_of_words_training(:,imTrack) = bags_of_words_training(:,imTrack)/length(closest_words);
                    imTrack = imTrack + 1;
                end
            end
            % Vector Quantisation (testing images)
            % disp('Encoding Test Images...')
            imTrack = 1;
            % Vector Quantisation
            for class = 1:10
                for image = 1:15
                    image_descriptors = desc_te(class,image);
                    image_descriptors = image_descriptors{1};
                    closest_words = knnsearch(words,image_descriptors');
                    for k = 1:length(closest_words)
                        bags_of_words_testing(closest_words(k),imTrack) = bags_of_words_testing(closest_words(k),imTrack) + 1;
                    end
                    bags_of_words_testing(:,imTrack) = bags_of_words_testing(:,imTrack)/length(closest_words);
                    imTrack = imTrack + 1;
                end
            end
            elapsed_time = toc; % stop timer for k-means
            time_store(2,kmeans_init,vocab_idx,iter_idx) = elapsed_time;
            % knn classification to indicate optimal vocabulary size
            knn_idx = knnsearch(bags_of_words_training', bags_of_words_testing');
            true_class_vector = reshape((ones(10,15).*[1:10]')',[150,1]);
            predicted_class_vector = true_class_vector(knn_idx);
            results_knn = sum(~logical(true_class_vector-predicted_class_vector))/length(true_class_vector);
            results_store(1,kmeans_init,vocab_idx,iter_idx) = results_knn;
            % nonlinear SVM classification
            t = templateSVM('KernelFunction','gaussian');
            svm_model = fitcecoc(bags_of_words_training',true_class_vector,'Learners',t);
            predicted_class_vector = predict(svm_model,bags_of_words_testing');
            results_svm = sum(~logical(true_class_vector-predicted_class_vector))/length(true_class_vector);
            results_store(2,kmeans_init,vocab_idx,iter_idx) = results_svm;
            % linear SVM classification
            svm_model = fitcecoc(bags_of_words_training',true_class_vector,'Learners','linear');
            predicted_class_vector = predict(svm_model,bags_of_words_testing');
            results_svm = sum(~logical(true_class_vector-predicted_class_vector))/length(true_class_vector);
            results_store(3,kmeans_init,vocab_idx,iter_idx) = results_svm;
        end
        iter_idx = iter_idx + 1;
    end
    vocab_idx = vocab_idx + 1;
end
save('BoW_sweep_results.mat','results_store','time_store')