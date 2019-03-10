import os, time
import matplotlib.pyplot as plt
import itertools
import pickle
import numpy as np
import imageio
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.autograd import Variable
from collections import OrderedDict

from scipy.stats import entropy # added


# G(z)
class generator(nn.Module):
    # initializers
    def __init__(self, d=128):
        super(generator, self).__init__()
        self.deconv1_1 = nn.ConvTranspose2d(100, d*2, 4, 1, 0)
        self.deconv1_1_bn = nn.BatchNorm2d(d*2)
        self.deconv1_2 = nn.ConvTranspose2d(10, d*2, 4, 1, 0)
        self.deconv1_2_bn = nn.BatchNorm2d(d*2)
        self.deconv2 = nn.ConvTranspose2d(d*4, d*2, 4, 2, 1)
        self.deconv2_bn = nn.BatchNorm2d(d*2)
        self.deconv3 = nn.ConvTranspose2d(d*2, d, 4, 2, 1)
        self.deconv3_bn = nn.BatchNorm2d(d)
        self.deconv4 = nn.ConvTranspose2d(d, 1, 4, 2, 1)

    # weight_init
    def weight_init(self, mean, std):
        for m in self._modules:
            normal_init(self._modules[m], mean, std)

    # forward method
    def forward(self, input, label):
        x = F.relu(self.deconv1_1_bn(self.deconv1_1(input)))
        y = F.relu(self.deconv1_2_bn(self.deconv1_2(label)))
        x = torch.cat([x, y], 1)
        x = F.relu(self.deconv2_bn(self.deconv2(x)))
        x = F.relu(self.deconv3_bn(self.deconv3(x)))
        x = F.tanh(self.deconv4(x))
        # x = F.relu(self.deconv4_bn(self.deconv4(x)))
        # x = F.tanh(self.deconv5(x))

        return x

class discriminator(nn.Module):
    # initializers
    def __init__(self, d=128):
        super(discriminator, self).__init__()
        self.conv1_1 = nn.Conv2d(1, d//2, 4, 2, 1)
        self.conv1_2 = nn.Conv2d(10, d//2, 4, 2, 1)
        self.conv2 = nn.Conv2d(d, d*2, 4, 2, 1)
        self.conv2_bn = nn.BatchNorm2d(d*2)
        self.conv3 = nn.Conv2d(d*2, d*4, 4, 2, 1)
        self.conv3_bn = nn.BatchNorm2d(d*4)
        self.conv4 = nn.Conv2d(d * 4, 1, 4, 1, 0)

    # weight_init
    def weight_init(self, mean, std):
        for m in self._modules:
            normal_init(self._modules[m], mean, std)

    # forward method
    def forward(self, input, label):
        x = F.leaky_relu(self.conv1_1(input), 0.2)
        y = F.leaky_relu(self.conv1_2(label), 0.2)
        x = torch.cat([x, y], 1)
        x = F.leaky_relu(self.conv2_bn(self.conv2(x)), 0.2)
        x = F.leaky_relu(self.conv3_bn(self.conv3(x)), 0.2)
        x = F.sigmoid(self.conv4(x))

        return x

def normal_init(m, mean, std):
    if isinstance(m, nn.ConvTranspose2d) or isinstance(m, nn.Conv2d):
        m.weight.data.normal_(mean, std)
        m.bias.data.zero_()
        
# CNN classifer network - LeNet

class LeNet5(nn.Module):
    """
    Input - 1x32x32
    C1 - 6@28x28 (5x5 kernel)
    tanh
    S2 - 6@14x14 (2x2 kernel, stride 2) Subsampling
    C3 - 16@10x10 (5x5 kernel, complicated shit)
    tanh
    S4 - 16@5x5 (2x2 kernel, stride 2) Subsampling
    C5 - 120@1x1 (5x5 kernel)
    F6 - 84
    tanh
    F7 - 10 (Output)
    """
    def __init__(self):
        super(LeNet5, self).__init__()

        self.convnet = nn.Sequential(OrderedDict([
            ('c1', nn.Conv2d(1, 6, kernel_size=(5, 5))),
            ('relu1', nn.ReLU()),
            ('s2', nn.MaxPool2d(kernel_size=(2, 2), stride=2)),
            ('c3', nn.Conv2d(6, 16, kernel_size=(5, 5))),
            ('relu3', nn.ReLU()),
            ('s4', nn.MaxPool2d(kernel_size=(2, 2), stride=2)),
            ('c5', nn.Conv2d(16, 120, kernel_size=(5, 5))),
            ('relu5', nn.ReLU())
        ]))

        self.fc = nn.Sequential(OrderedDict([
            ('f6', nn.Linear(120, 84)),
            ('relu6', nn.ReLU()),
            ('f7', nn.Linear(84, 10)),
            ('sig7', nn.LogSoftmax(dim=-1))
        ]))

    def forward(self, img):
        output = self.convnet(img)
        output = output.view(img.size(0), -1)
        output = self.fc(output)
        return output        


# fixed noise & label
temp_z_ = torch.randn(10, 100)
fixed_z_ = temp_z_
fixed_y_ = torch.zeros(10, 1)
for i in range(9):
    fixed_z_ = torch.cat([fixed_z_, temp_z_], 0)
    temp = torch.ones(10, 1) + i
    fixed_y_ = torch.cat([fixed_y_, temp], 0)

fixed_z_ = fixed_z_.view(-1, 100, 1, 1)
fixed_y_label_ = torch.zeros(100, 10)
fixed_y_label_.scatter_(1, fixed_y_.type(torch.LongTensor), 1)
fixed_y_label_ = fixed_y_label_.view(-1, 10, 1, 1)
fixed_z_, fixed_y_label_ = Variable(fixed_z_.cuda(), volatile=True), Variable(fixed_y_label_.cuda(), volatile=True)
def show_result(num_epoch, show = False, save = False, path = 'result.png'):

    G.eval()
    test_images = G(fixed_z_, fixed_y_label_)
    G.train()

    size_figure_grid = 10
    fig, ax = plt.subplots(size_figure_grid, size_figure_grid, figsize=(5, 5))
    for i, j in itertools.product(range(size_figure_grid), range(size_figure_grid)):
        ax[i, j].get_xaxis().set_visible(False)
        ax[i, j].get_yaxis().set_visible(False)

    for k in range(10*10):
        i = k // 10
        j = k % 10
        ax[i, j].cla()
        ax[i, j].imshow(test_images[k, 0].cpu().data.numpy(), cmap='gray')

    label = 'Epoch {0}'.format(num_epoch)
    fig.text(0.5, 0.04, label, ha='center')
    plt.savefig(path)

    if show:
        plt.show()
    else:
        plt.close()

# def show_train_hist(hist, show = False, save = False, path = 'Train_hist.png'):
#     x = range(len(hist['D_losses']))

#     y1 = hist['D_losses']
#     y2 = hist['G_losses']

#     plt.plot(x, y1, label='D_loss')
#     plt.plot(x, y2, label='G_loss')

#     plt.xlabel('Epoch')
#     plt.ylabel('Loss')

#     plt.legend(loc=4)
#     plt.grid(True)
#     plt.tight_layout()

#     if save:
#         plt.savefig(path)

#     if show:
#         plt.show()
#     else:
#         plt.close()

# training parameters
batch_size = 128
lr = 0.0002
train_epoch = 300

classifer = LeNet5().cuda()
classifer.load_state_dict(torch.load('./LeNet.pth'))

# Classification parameters
num_test = 1000

# data_loader
img_size = 32
transform = transforms.Compose([
        transforms.Scale(img_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
])
train_loader = torch.utils.data.DataLoader(
    datasets.MNIST('data', train=True, download=True, transform=transform),
    batch_size=batch_size, shuffle=True)

# network
G = generator(64) # CHANGED
D = discriminator(64)
G.weight_init(mean=0.0, std=0.02)
D.weight_init(mean=0.0, std=0.02)
G.cuda()
D.cuda()

# Binary Cross Entropy loss
BCE_loss = nn.BCELoss()

# Adam optimizer
G_optimizer = optim.Adam(G.parameters(), lr=lr, betas=(0.5, 0.999))
D_optimizer = optim.Adam(D.parameters(), lr=lr, betas=(0.5, 0.999))

# results save folder
root = 'MNIST_cDCGAN_results/'
model = 'MNIST_cDCGAN_'
os.makedirs('MNIST_cDCGAN_results', exist_ok=True)
os.makedirs('MNIST_cDCGAN_results/Fixed_results', exist_ok=True)
os.makedirs('MNIST_cDCGAN_results/Losses', exist_ok=True)
total_store = []
mean_inception_store = []
std_inception_store = []

# label preprocess
onehot = torch.zeros(10, 10)
onehot = onehot.scatter_(1, torch.LongTensor([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]).view(10,1), 1).view(10, 10, 1, 1)
fill = torch.zeros([10, 10, img_size, img_size])
for i in range(10):
    fill[i, i, :, :] = 1

epoch_G_losses = []
epoch_D_losses = []

print('training start!')
start_time = time.time()
for epoch in range(train_epoch):
    D_losses = []
    G_losses = []
    G.train()
    

    # learning rate decay
    # if (epoch+1) == 11:
    #     G_optimizer.param_groups[0]['lr'] /= 10
    #     D_optimizer.param_groups[0]['lr'] /= 10
    #     print("learning rate change!")

    # if (epoch+1) == 16:
    #     G_optimizer.param_groups[0]['lr'] /= 10
    #     D_optimizer.param_groups[0]['lr'] /= 10
    #     print("learning rate change!")

    epoch_start_time = time.time()
    y_real_ = torch.ones(batch_size)
    y_fake_ = torch.zeros(batch_size)
    y_real_, y_fake_ = Variable(y_real_.cuda()), Variable(y_fake_.cuda())
    for x_, y_ in train_loader:
        # train discriminator D
        D.zero_grad()

        mini_batch = x_.size()[0]

        if mini_batch != batch_size:
            y_real_ = torch.ones(mini_batch)
            y_fake_ = torch.zeros(mini_batch)
            y_real_, y_fake_ = Variable(y_real_.cuda()), Variable(y_fake_.cuda())

        y_fill_ = fill[y_]
        x_, y_fill_ = Variable(x_.cuda()), Variable(y_fill_.cuda())

        D_result = D(x_, y_fill_).squeeze()
        D_real_loss = BCE_loss(D_result, y_real_)

        z_ = torch.randn((mini_batch, 100)).view(-1, 100, 1, 1)
        y_ = (torch.rand(mini_batch, 1) * 10).type(torch.LongTensor).squeeze()
        y_label_ = onehot[y_]
        y_fill_ = fill[y_]
        z_, y_label_, y_fill_ = Variable(z_.cuda()), Variable(y_label_.cuda()), Variable(y_fill_.cuda())

        G_result = G(z_, y_label_)
        D_result = D(G_result, y_fill_).squeeze()

        D_fake_loss = BCE_loss(D_result, y_fake_)
        D_fake_score = D_result.data.mean()

        D_train_loss = D_real_loss + D_fake_loss

        D_train_loss.backward()
        D_optimizer.step()

        D_losses.append(D_train_loss.data.item())

        # train generator G
        G.zero_grad()

        z_ = torch.randn((mini_batch, 100)).view(-1, 100, 1, 1)
        y_ = (torch.rand(mini_batch, 1) * 10).type(torch.LongTensor).squeeze()
        y_label_ = onehot[y_]
        y_fill_ = fill[y_]
        z_, y_label_, y_fill_ = Variable(z_.cuda()), Variable(y_label_.cuda()), Variable(y_fill_.cuda())

        G_result = G(z_, y_label_)
        D_result = D(G_result, y_fill_).squeeze()

        G_train_loss = BCE_loss(D_result, y_real_)

        G_train_loss.backward()
        G_optimizer.step()

        G_losses.append(G_train_loss.data.item())

    epoch_end_time = time.time()
    per_epoch_ptime = epoch_end_time - epoch_start_time

    epoch_G_losses.append(torch.mean(torch.FloatTensor(G_losses)))
    epoch_D_losses.append(torch.mean(torch.FloatTensor(D_losses)))

    print('[%d/%d] - ptime: %.2f, loss_d: %.3f, loss_g: %.3f' % ((epoch + 1), train_epoch, per_epoch_ptime, torch.mean(torch.FloatTensor(D_losses)),
                                                              torch.mean(torch.FloatTensor(G_losses))))
    fixed_p = root + 'Fixed_results/' + model + str(epoch + 1) + '.png'
    show_result((epoch+1), save=True, path=fixed_p)

    scores = []
    
    temp_z_ = torch.randn(num_test, 100)
    fixed_z_ = temp_z_
    fixed_y_ = torch.zeros(num_test, 1)
    for i in range(9):
        temp_z_ = torch.randn(num_test, 100)
        fixed_z_ = torch.cat([fixed_z_, temp_z_], 0)
        temp = torch.ones(num_test, 1) + i
        fixed_y_ = torch.cat([fixed_y_, temp], 0)
    
    fixed_z_ = fixed_z_.view(-1, 100, 1, 1)
    fixed_y_label_ = torch.zeros(10*num_test, 10)
    fixed_y_label_.scatter_(1, fixed_y_.type(torch.LongTensor), 1)
    fixed_y_label_ = fixed_y_label_.view(-1, 10, 1, 1)
    fixed_z_, fixed_y_label_ = Variable(fixed_z_.cuda(), volatile=True), Variable(fixed_y_label_.cuda(), volatile=True)
    #test_images = G(fixed_z_, fixed_y_label_)
    path = 'test.png'
    
    G.eval()
    test_images = G(fixed_z_, fixed_y_label_)
        
    # Class & average accuracies --
    output = classifer(test_images)
    #avg_loss += criterion(output, labels).sum()
    pred = output.detach().max(1)[1]
    pred =pred.detach().cpu()
    fixed_y_=(fixed_y_.detach().cpu())
    fixed_y_ = fixed_y_.long()
    total_correct_labs = []
    for i in range(10):
        total_correct_labs.append(pred[(i*num_test):((i+1)*num_test)].eq(fixed_y_[(i*num_test):((i+1)*num_test)].view_as(pred[(i*num_test):((i+1)*num_test)].long())).sum())
        
    total = np.mean(total_correct_labs)/num_test
    
    # Inception score -------------
    output_softmax = torch.exp(output)
    output_softmax = output_softmax.detach().cpu().numpy()
    #output_softmax = F.softmax(output_dlogged).cpu().numpy() # convert to probabilities 
    
    split_scores = []
    n_splits = 10
    
    shuffle_perm = np.random.permutation(num_test*10)# need to shuffle data, as is currently ordered    
    for k in range(n_splits):
        shuffle_part = shuffle_perm[k*((num_test*10)//n_splits):(k+1)*((num_test*10)//n_splits)]
        part = output_softmax[shuffle_part,:]
        py = np.mean(part, axis=0)
        scores = []
        for i in range(part.shape[0]):
            pyx = part[i, :]
            scores.append(entropy(pyx, py)) # ENTROPY CAN BE FOUND IN SCIPY LIBRARY, SEE IMPORTS!
        split_scores.append(np.exp(np.mean(scores)))
    
    mean_inception = np.mean(split_scores)
    mean_inception_store.append(mean_inception)
    std_inception = np.std(split_scores)
    std_inception_store.append(std_inception)
    total_store.append(total)
    print('Score:{}'.format(total))
    print('Mean Inception Score:{}'.format(mean_inception))
    print('Std Inception Score:{}'.format(std_inception))

#print("Avg one epoch ptime: %.2f, total %d epochs ptime: %.2f" % (torch.mean(torch.FloatTensor(train_hist['per_epoch_ptimes'])), train_epoch, total_ptime))
print("Training finish!... save training results")

np.savetxt('MNIST_cDCGAN_results/Losses/GLoss.txt',epoch_G_losses,delimiter='\n') # SAVE THESE RESULTS WHERE?
np.savetxt('MNIST_cDCGAN_results/Losses/DLoss.txt',epoch_D_losses,delimiter='\n')


end_time = time.time()
total_ptime = end_time - start_time




np.savetxt('MNIST_cDCGAN_results/Losses/performance_epoch{}.txt'.format(epoch),[total_store])
np.savetxt('MNIST_cDCGAN_results/Losses/mean_inc_epoch{}.txt'.format(epoch),mean_inception_store)
np.savetxt('MNIST_cDCGAN_results/Losses/std_inc_epoch{}.txt'.format(epoch),std_inception_store)
 
    