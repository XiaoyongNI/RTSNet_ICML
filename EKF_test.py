import torch.nn as nn
import torch
import time
from EKF import ExtendedKalmanFilter


def EKFTest(SysModel, test_input, test_target, allStates=True, randomInit = False,test_init=None):

    N_T = test_target.size()[0]

    # LOSS
    loss_fn = nn.MSELoss(reduction='mean')
    
    # MSE [Linear]
    MSE_EKF_linear_arr = torch.empty(N_T)
    start = time.time()
    EKF = ExtendedKalmanFilter(SysModel)

    KG_array = torch.zeros_like(EKF.KG_array)
    # Allocate empty list for output
    EKF_out = []
    j=0
    
    for sequence_target,sequence_input in zip(test_target,test_input):

        if(randomInit):
            EKF.InitSequence(torch.unsqueeze(test_init[j,:],1), SysModel.m2x_0)
        else:       
            EKF.InitSequence(SysModel.m1x_0, SysModel.m2x_0)
        
        EKF.GenerateSequence(sequence_input, sequence_input.size()[-1])

        if(allStates):
            MSE_EKF_linear_arr[j] = loss_fn(EKF.x, sequence_target).item()
        else:
            loc = torch.tensor([True,False,False]) # for position only
            MSE_EKF_linear_arr[j] = loss_fn(EKF.x[loc,:], sequence_target[loc,:]).item()
        KG_array = torch.add(EKF.KG_array, KG_array) 
        EKF_out.append(EKF.x)
        j = j+1
    end = time.time()
    t = end - start
    # Average KG_array over Test Examples
    KG_array /= N_T

    MSE_EKF_linear_avg = torch.mean(MSE_EKF_linear_arr)
    MSE_EKF_dB_avg = 10 * torch.log10(MSE_EKF_linear_avg)

    # Standard deviation
    MSE_EKF_linear_std = torch.std(MSE_EKF_linear_arr, unbiased=True)

    # Confidence interval
    EKF_std_dB = 10 * torch.log10(MSE_EKF_linear_std + MSE_EKF_linear_avg) - MSE_EKF_dB_avg
    
    print("Extended Kalman Filter - MSE LOSS:", MSE_EKF_dB_avg, "[dB]")
    print("Extended Kalman Filter - STD:", EKF_std_dB, "[dB]")
    # Print Run Time
    print("Inference Time:", t)

    return [MSE_EKF_linear_arr, MSE_EKF_linear_avg, MSE_EKF_dB_avg, KG_array, EKF_out]


# def EKFTest_evol(SysModel, test_input, test_target, modelKnowledge = 'full'):

#     N_T = test_target.size()[0]

#     # LOSS
#     loss_fn = nn.MSELoss(reduction='none')
    
#     # MSE [Linear]
#     MSE_EKF_linear_arr = torch.empty(N_T,SysModel.m, SysModel.T_test)
#     EKF = ExtendedKalmanFilter(SysModel, modelKnowledge)
#     EKF.InitSequence(SysModel.m1x_0, SysModel.m2x_0)

#     KG_array = torch.empty([N_T, SysModel.T_test, SysModel.m, SysModel.n])
#     KG_trace = torch.empty([SysModel.T_test])
#     EKF_out = torch.empty([N_T, SysModel.m, SysModel.T_test])
    
#     for j in range(0, N_T):
#         EKF.GenerateSequence(test_input[j, :, :], EKF.T_test)

#         MSE_EKF_linear_arr[j,:,:] = loss_fn(EKF.x, test_target[j, :, :])
#         KG_array[j,:,:,:] = EKF.KG_array
#         EKF_out[j,:,:] = EKF.x
#     # Average KG_array over Test Examples

#     KG_avg = torch.mean(KG_array,0)
#     for j in range(0, SysModel.T_test):
#         KG_trace[j] = torch.trace(KG_avg[j,:,:])

#     MSE_EKF_linear_avg = torch.mean(MSE_EKF_linear_arr, [0,1])
#     MSE_EKF_dB_avg = 10 * torch.log10(MSE_EKF_linear_avg)
#     trace_dB_avg = 10* torch.log10(KG_trace)

#     return [MSE_EKF_dB_avg, trace_dB_avg]



