import torch
torch.pi = torch.acos(torch.zeros(1)).item() * 2 # which is 3.1415927410125732
import torch.nn as nn
from EKF_test import EKFTest
from Extended_RTS_Smoother_test import S_Test
from ParticleSmoother_test import PSTest

from Extended_sysmdl import SystemModel
from Extended_data import DataGen,DataLoader,DataLoader_GPU, Decimate_and_perturbate_Data,Short_Traj_Split,wandb_switch
from Extended_data import N_E, N_CV, N_T
from Pipeline_ERTS import Pipeline_ERTS as Pipeline
from Pipeline_EKF import Pipeline_EKF
from Pipeline_concat_models import Pipeline_twoRTSNets

# from PF_test import PFTest

from datetime import datetime

from KalmanNet_nn import KalmanNetNN
from RTSNet_nn import RTSNetNN
from ERTSNet.RTSNet_LMMSEh import RTSNetNN as RTSNet_lmmseh

from RTSNet_nn_multipass import RTSNetNN_multipass
from Pipeline_ERTS_multipass import Pipeline_ERTS as Pipeline_multipass

from Plot import Plot_extended as Plot

if wandb_switch:
   import wandb
   wandb.init(project="RTSNet_DT_NLobs")

from filing_paths import path_model
import sys
sys.path.insert(1, path_model)
from parameters import T, T_test, m1x_0, m2x_0, m, n,H_mod
from model import f, h, h_nonlinear, toCartesian, getJacobian

if torch.cuda.is_available():
   dev = torch.device("cuda:0")  # you can continue going on here, like cuda:1 cuda:2....etc.
   torch.set_default_tensor_type('torch.cuda.FloatTensor')
   print("Running on the GPU")
else:
   dev = torch.device("cpu")
   print("Running on the CPU")


print("Pipeline Start")
################
### Get Time ###
################
today = datetime.today()
now = datetime.now()
strToday = today.strftime("%m.%d.%y")
strNow = now.strftime("%H:%M:%S")
strTime = strToday + "_" + strNow
print("Current Time =", strTime)

###################
###  Settings   ###
###################
offset = 0
chop = False
sequential_training = False
path_results = 'ERTSNet/'
DatafolderName = 'Simulations/Lorenz_Atractor/data/T20_hNL' + '/'

r2 = torch.tensor([1e-3])
# r2 = torch.tensor([100, 10, 1, 0.1, 0.01])
r = torch.sqrt(r2)
vdB = 0 # ratio v=q2/r2
v = 10**(vdB/10)

q2 = torch.mul(v,r2)
q = torch.sqrt(q2)

# q and r optimized for EKF and MB RTS
# r2optdB = torch.tensor([16.9897])
# ropt = torch.sqrt(10**(-r2optdB/10))
# q2optdB = torch.tensor([28.2391])
# qopt = torch.sqrt(10**(-q2optdB/10))

print("1/r2 [dB]: ", 10 * torch.log10(1/r[0]**2))
print("1/q2 [dB]: ", 10 * torch.log10(1/q[0]**2))

# traj_resultName = ['traj_lor_KNetFull_rq1030_T2000_NT100.pt']#,'partial_lor_r4.pt','partial_lor_r5.pt','partial_lor_r6.pt']
dataFileName = ['data_lor_v0_rq3030_T20.pt']#,'data_lor_v20_r1e-2_T100.pt','data_lor_v20_r1e-3_T100.pt','data_lor_v20_r1e-4_T100.pt']
# KFRTSResultName = 'KFRTS_partialh_rq3050_T2000' 

#########################################
###  Generate and load data DT case   ###
#########################################

sys_model = SystemModel(f, q[0], h_nonlinear, r[0], T, T_test, m, n)# parameters for GT
sys_model.InitSequence(m1x_0, m2x_0)# x0 and P0
# print("Start Data Gen")
# DataGen(sys_model, DatafolderName + dataFileName[0], T, T_test,randomInit=False)
print("Data Load")
print(dataFileName[0])
[train_input_long,train_target_long, cv_input, cv_target, test_input, test_target] =  torch.load(DatafolderName + dataFileName[0],map_location=dev)  
if chop: 
   print("chop training data")    
   [train_target, train_input, train_init] = Short_Traj_Split(train_target_long, train_input_long, T)
   # [cv_target, cv_input] = Short_Traj_Split(cv_target, cv_input, T)
else:
   print("no chopping") 
   train_target = train_target_long[:,:,0:T]
   train_input = train_input_long[:,:,0:T] 
   # cv_target = cv_target[:,:,0:T]
   # cv_input = cv_input[:,:,0:T]  

print("trainset size:",train_target.size())
print("cvset size:",cv_target.size())
print("testset size:",test_target.size())


##########################################
### Evaluate Lower Bound (KS with H=I) ###
##########################################
# N_T = len(test_target)
# test_input_LB = []

# for j in range(0, N_T): 
#    # Observations; additive Gaussian Noise  
#    test_input_LB.append(test_target[j] + torch.randn_like(test_target[j]) * r[0])

# # Model with H=I          
# sys_model_LB = SystemModel(f, q[0], h, r[0], T, T_test, m, n)
# sys_model_LB.InitSequence(m1x_0, m2x_0)
# print("Evaluate ERTS H=I")
# S_Test(sys_model_LB, test_input_LB, test_target)



######################################
### Evaluate Filters and Smoothers ###
######################################
### Evaluate EKF full
# print("Evaluate EKF full")
# [MSE_EKF_linear_arr, MSE_EKF_linear_avg, MSE_EKF_dB_avg, EKF_KG_array, EKF_out] = EKFTest(sys_model, test_input, test_target)

### Evaluate RTS full
# print("Evaluate RTS full")
# [MSE_ERTS_linear_arr, MSE_ERTS_linear_avg, MSE_ERTS_dB_avg, ERTS_out] = S_Test(sys_model, test_input, test_target)

### Evaluate Particle Smoother
# print("Evaluate Particle Smoother full")
# [MSE_PS_linear_arr, MSE_PS_linear_avg, MSE_PS_dB_avg, PS_out, t_PS] = PSTest(sys_model, test_input, test_target,N_FWParticles=100, M_BWTrajs=10, init_cond=None)


# Save results

# KFRTSfolderName = 'ERTSNet' + '/'
# torch.save({'MSE_EKF_linear_arr': MSE_EKF_linear_arr,
#             'MSE_EKF_dB_avg': MSE_EKF_dB_avg,
#             'MSE_ERTS_linear_arr': MSE_ERTS_linear_arr,
#             'MSE_ERTS_dB_avg': MSE_ERTS_dB_avg,
#             }, KFRTSfolderName+KFRTSResultName)

# # Save trajectories
# trajfolderName = 'KNet' + '/'
# DataResultName = traj_resultName[rindex]
# EKF_sample = torch.reshape(EKF_out[0,:,:],[1,m,T_test])
# target_sample = torch.reshape(test_target[0,:,:],[1,m,T_test])
# input_sample = torch.reshape(test_input[0,:,:],[1,n,T_test])
# KNet_sample = torch.reshape(KNet_test[0,:,:],[1,m,T_test])
# torch.save({
#             'KNet': KNet_test,
#             }, trajfolderName+DataResultName)

# ## Save histogram
# EKFfolderName = 'KNet' + '/'
# torch.save({'KNet_MSE_test_linear_arr': KNet_MSE_test_linear_arr,
#             'KNet_MSE_test_dB_avg': KNet_MSE_test_dB_avg,
#             }, EKFfolderName+EKFResultName)

###################################
### Test reversed input and H=I ###
###################################
## Model with H=I          
sys_model_H = SystemModel(f, q[0], h, r[0], T, T_test, m, n)
sys_model_H.InitSequence(m1x_0, m2x_0)

## reverse input h^-1(x)
# N_T = len(test_input)
# train_input_reversed = torch.zeros_like(test_input)
# test_input_reversed = torch.zeros_like(test_input)

# for i in range(0, N_T): 
#    for j in range(0,T_test):
#       test_input_reversed[i,:,j]=toCartesian(test_input[i,:,j])

## Evaluate reversed input
# loss_obs = nn.MSELoss(reduction='mean')
# MSE_obs_linear_arr = torch.empty(N_T)# MSE [Linear]
# for j in range(0, N_T):      
#    MSE_obs_linear_arr[j] = loss_obs(test_input_reversed[j,:,:], test_target[j]).item()
# MSE_obs_linear_avg = torch.mean(MSE_obs_linear_arr)
# MSE_obs_dB_avg = 10 * torch.log10(MSE_obs_linear_avg)
# # Standard deviation
# MSE_obs_linear_std = torch.std(MSE_obs_linear_arr, unbiased=True)
# # Confidence interval
# obs_std_dB = 10 * torch.log10(MSE_obs_linear_std + MSE_obs_linear_avg) - MSE_obs_dB_avg
# print("Observation Noise Floor(test dataset) - MSE LOSS:", MSE_obs_dB_avg, "[dB]")
# print("Observation Noise Floor(test dataset) - STD:", obs_std_dB, "[dB]")

# # #Evaluate RTS full
# print("Evaluate RTS H=I")
# [MSE_ERTS_linear_arr, MSE_ERTS_linear_avg, MSE_ERTS_dB_avg, ERTS_out] = S_Test(sys_model_H, test_input_reversed, test_target)

## RTSNet with reverse input h^-1(x)
# Build Neural Network
# print("RTSNet with full model info")
# RTSNet_model = RTSNetNN()
# RTSNet_model.NNBuild(sys_model_H, KNet_in_mult = 5, KNet_out_mult = 40, RTSNet_in_mult = 5, RTSNet_out_mult = 40)
# # ## Train Neural Network
# RTSNet_Pipeline = Pipeline(strTime, "RTSNet", "RTSNet")
# RTSNet_Pipeline.setssModel(sys_model_H)
# RTSNet_Pipeline.setModel(RTSNet_model)
# print("Number of trainable parameters for RTSNet:",sum(p.numel() for p in RTSNet_model.parameters() if p.requires_grad))
# RTSNet_Pipeline.setTrainingParams(n_Epochs=1000, n_Batch=10, learningRate=1e-5, weightDecay=1e-9) 
# # RTSNet_Pipeline.model = torch.load('ERTSNet/best-model_DTfull_rq3050_T2000.pt',map_location=dev)
# if(chop):
#    [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model_H, cv_input_reversed, cv_target, train_input_reversed, train_target, path_results,randomInit=True,train_init=train_init)
# else:
#    [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model_H, cv_input_reversed, cv_target, train_input_reversed, train_target, path_results)
# ## Test Neural Network
# [MSE_test_linear_arr, MSE_test_linear_avg, MSE_test_dB_avg,rtsnet_out,RunTime] = RTSNet_Pipeline.NNTest(sys_model_H, test_input_reversed, test_target, path_results)

## RTSNet with reverse input linear MMSE method
# Build Neural Network
# print("RTSNet with LMMSE of Jacobian of h")
# RTSNet_model = RTSNet_lmmseh()
# RTSNet_model.NNBuild(sys_model, KNet_in_mult = 40, KNet_out_mult = 5, RTSNet_in_mult = 40, RTSNet_out_mult = 5)
# # ## Train Neural Network
# RTSNet_Pipeline = Pipeline(strTime, "RTSNet", "RTSNet")
# RTSNet_Pipeline.setssModel(sys_model)
# RTSNet_Pipeline.setModel(RTSNet_model)
# print("Number of trainable parameters for RTSNet:",sum(p.numel() for p in RTSNet_model.parameters() if p.requires_grad))
# RTSNet_Pipeline.setTrainingParams(n_Epochs=2000, n_Batch=100, learningRate=1e-4, weightDecay=1e-4) 
# # RTSNet_Pipeline.model = torch.load('ERTSNet/best-model_DTfull_rq3050_T2000.pt',map_location=dev)
# if(chop):
#    [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model, cv_input, cv_target, train_input, train_target, path_results,CompositionLoss=True,randomInit=True,train_init=train_init)
# else:
#    [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model, cv_input, cv_target, train_input, train_target, path_results,CompositionLoss=True)
# ## Test Neural Network
# [MSE_test_linear_arr, MSE_test_linear_avg, MSE_test_dB_avg,rtsnet_out,RunTime] = RTSNet_Pipeline.NNTest(sys_model, test_input, test_target, path_results)


#######################
### Evaluate RTSNet ###
#######################
## RTSNet with full info
## Build Neural Network
# print("RTSNet with full model info")
# RTSNet_model = RTSNetNN()
# CompositionLoss = True
# RTSNet_model.NNBuild(sys_model, KNet_in_mult = 40, KNet_out_mult = 5, RTSNet_in_mult = 40, RTSNet_out_mult = 5)
# ## Train Neural Network
# RTSNet_Pipeline = Pipeline(strTime, "RTSNet", "RTSNet")
# RTSNet_Pipeline.setssModel(sys_model)
# RTSNet_Pipeline.setModel(RTSNet_model)
# print("Number of trainable parameters for RTSNet:",sum(p.numel() for p in RTSNet_model.parameters() if p.requires_grad))
# RTSNet_Pipeline.setTrainingParams(n_Epochs=2000, n_Batch=100, learningRate=1e-4, weightDecay=1e-4) 
# # RTSNet_Pipeline.model = torch.load('ERTSNet/best-model_DTfull_rq3050_T2000.pt',map_location=dev)
# if(chop):
#    [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model, cv_input, cv_target, train_input, train_target, path_results,randomInit=True,train_init=train_init)
# else:
#    print("Composition Loss:",CompositionLoss)
#    [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model, cv_input, cv_target, train_input, train_target, path_results,CompositionLoss=CompositionLoss)
# ## Test Neural Network
# [MSE_test_linear_arr, MSE_test_linear_avg, MSE_test_dB_avg,rtsnet_out,RunTime] = RTSNet_Pipeline.NNTest(sys_model, test_input, test_target, path_results)


###############################################
### Concat two RTSNets with model mismatch  ###
###############################################
### Train pass2 on the output of pass1
print("test pass1 on Train Set")
fileName = "Simulations/Lorenz_Atractor/data/T20_hNL/Pass1_rq3030_T20.pt"
# [MSE_test_linear_arr, MSE_test_linear_avg, MSE_test_dB_avg,rtsnet_out_train,RunTime] = RTSNet_Pipeline.NNTest(sys_model, train_input, train_target, path_results)
# cv_input_pass2 = rtsnet_out_train[0:N_CV]
# cv_target_pass2 = train_target[0:N_CV]
# train_input_pass2 = rtsnet_out_train[N_CV:-1]
# train_target_pass2 = train_target[N_CV:-1]
# torch.save([train_input_pass2, train_target_pass2, cv_input_pass2, cv_target_pass2], fileName)
[train_input_pass2, train_target_pass2, cv_input_pass2, cv_target_pass2] = torch.load(fileName, map_location=dev)

print("Train RTSNet pass2")
RTSNet_model = RTSNetNN()
RTSNet_model.NNBuild(sys_model_H, KNet_in_mult = 5, KNet_out_mult = 40, RTSNet_in_mult = 5, RTSNet_out_mult = 40)
## Train Neural Network
RTSNet_Pipeline = Pipeline(strTime, "RTSNet", "RTSNet")
RTSNet_Pipeline.setssModel(sys_model_H)
RTSNet_Pipeline.setModel(RTSNet_model)
print("Number of trainable parameters for RTSNet:",sum(p.numel() for p in RTSNet_model.parameters() if p.requires_grad))
RTSNet_Pipeline.setTrainingParams(n_Epochs=2000, n_Batch=100, learningRate=1e-4, weightDecay=1e-4) 
### Optinal: record parameters to wandb
if wandb_switch:
   wandb.log({
   "learning_rate_pass2": RTSNet_Pipeline.learningRate,
   "batch_size_pass2": RTSNet_Pipeline.N_B,
   "weight_decay_pass2": RTSNet_Pipeline.weightDecay})
if(chop):
   [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model_H, cv_input_pass2, cv_target_pass2, train_input_pass2, train_target_pass2, path_results,randomInit=True,train_init=train_init)
else:
   [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model_H, cv_input_pass2, cv_target_pass2, train_input_pass2, train_target_pass2, path_results)


## load trained Neural Network
print("RTSNet with model mismatch")
RTSNet_model1 = torch.load('ERTSNet/new_arch_LA/DT/HNL/rq3030_T20.pt',map_location=dev)
RTSNet_model2 = torch.load('ERTSNet/best-model.pt',map_location=dev)
## Setup Pipeline
RTSNet_Pipeline = Pipeline_twoRTSNets(strTime, "RTSNet", "RTSNet")
RTSNet_Pipeline.setModel(RTSNet_model1, RTSNet_model2)
NumofParameter = RTSNet_Pipeline.count_parameters()
print("Number of parameters for RTSNet: ",NumofParameter)
## Test Neural Network
[MSE_test_linear_arr, MSE_test_linear_avg, MSE_test_dB_avg,rtsnet_out_2pass,RunTime] = RTSNet_Pipeline.NNTest(sys_model, test_input, test_target, path_results)


########################
### RTSNet Multipass ###
########################
## Build Neural Network
# print("RTSNet multipass")
# iterations = 2 # number of passes
# RTSNet_model = RTSNetNN_multipass(iterations)
# RTSNet_model.NNBuild_multipass(sys_model)
# ## Train Neural Network
# RTSNet_Pipeline = Pipeline_multipass(strTime, "RTSNet", "RTSNet")
# RTSNet_Pipeline.setModel(RTSNet_model)
# RTSNet_Pipeline.setTrainingParams(n_Epochs=2000, n_Batch=100, learningRate=1e-4, weightDecay=1e-4)
# NumofParameter = RTSNet_Pipeline.count_parameters()
# if(chop):
#    [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model, cv_input, cv_target, train_input, train_target, path_results,CompositionLoss=True,randomInit=True,train_init=train_init)
# else:
#    [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model, cv_input, cv_target, train_input, train_target, path_results,CompositionLoss=True)
# ## Test Neural Network
# # RTSNet_Pipeline.model = torch.load('ERTSNet/model_KNetNew_DT_procmis_r30q50_T2000.pt',map_location=cuda0)
# [MSE_test_linear_arr, MSE_test_linear_avg, MSE_test_dB_avg,rtsnet_out,RunTime] = RTSNet_Pipeline.NNTest(sys_model, test_input, test_target, path_results)
   





