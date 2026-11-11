# Colab session 1: dry-run evidence

Recorded on the laptop on 2026-11-11 after the session. The notebook's section 8 printed the dry run on Colab
but did not save it to Drive, and the Colab tab was closed before the full output was copied.

Observed on Colab (read from the notebook output during the session, partial):
- batches 8, 9 and 10 listed with "0/10 done" each (r1_Dctl*, r1_U_s*, r1_Uctl*), followed by
  "Training disabled: no batch was trained in this cell."

The dry run is deterministic for a given commit (it reads only the committed matrix and protocol files).
The full plan below was generated locally from the same commit (ac0715a), with no storage, so every batch
shows 0/10 done:

```
Milestone 3B dry run (design D, r1 PROPOSED): 110 fits in 11 batches of 10
split 50bd994880abbe15..., population 62bd9a74c71f..., groups 6df0855dc0c5...
laptop-CPU estimate 2.7-4.3 h (measured 1.45-2.36 min/fit); Colab speed NOT measured; storage ~3.2 GB at ~30 MB/run
  batch  0: 0/10 done  r1_full_s0, r1_full_s1, r1_full_s2, r1_full_s3, r1_full_s4, r1_full_s5, r1_full_s6, r1_full_s7, r1_full_s8, r1_full_s9
  batch  1: 0/10 done  r1_A_s0, r1_A_s1, r1_A_s2, r1_A_s3, r1_A_s4, r1_A_s5, r1_A_s6, r1_A_s7, r1_A_s8, r1_A_s9
  batch  2: 0/10 done  r1_Actl0_s0, r1_Actl1_s1, r1_Actl2_s2, r1_Actl3_s3, r1_Actl4_s4, r1_Actl5_s5, r1_Actl6_s6, r1_Actl7_s7, r1_Actl8_s8, r1_Actl9_s9
  batch  3: 0/10 done  r1_B_s0, r1_B_s1, r1_B_s2, r1_B_s3, r1_B_s4, r1_B_s5, r1_B_s6, r1_B_s7, r1_B_s8, r1_B_s9
  batch  4: 0/10 done  r1_Bctl0_s0, r1_Bctl1_s1, r1_Bctl2_s2, r1_Bctl3_s3, r1_Bctl4_s4, r1_Bctl5_s5, r1_Bctl6_s6, r1_Bctl7_s7, r1_Bctl8_s8, r1_Bctl9_s9
  batch  5: 0/10 done  r1_C_s0, r1_C_s1, r1_C_s2, r1_C_s3, r1_C_s4, r1_C_s5, r1_C_s6, r1_C_s7, r1_C_s8, r1_C_s9
  batch  6: 0/10 done  r1_Cctl0_s0, r1_Cctl1_s1, r1_Cctl2_s2, r1_Cctl3_s3, r1_Cctl4_s4, r1_Cctl5_s5, r1_Cctl6_s6, r1_Cctl7_s7, r1_Cctl8_s8, r1_Cctl9_s9
  batch  7: 0/10 done  r1_D_s0, r1_D_s1, r1_D_s2, r1_D_s3, r1_D_s4, r1_D_s5, r1_D_s6, r1_D_s7, r1_D_s8, r1_D_s9
  batch  8: 0/10 done  r1_Dctl0_s0, r1_Dctl1_s1, r1_Dctl2_s2, r1_Dctl3_s3, r1_Dctl4_s4, r1_Dctl5_s5, r1_Dctl6_s6, r1_Dctl7_s7, r1_Dctl8_s8, r1_Dctl9_s9
  batch  9: 0/10 done  r1_U_s0, r1_U_s1, r1_U_s2, r1_U_s3, r1_U_s4, r1_U_s5, r1_U_s6, r1_U_s7, r1_U_s8, r1_U_s9
  batch 10: 0/10 done  r1_Uctl0_s0, r1_Uctl1_s1, r1_Uctl2_s2, r1_Uctl3_s3, r1_Uctl4_s4, r1_Uctl5_s5, r1_Uctl6_s6, r1_Uctl7_s7, r1_Uctl8_s8, r1_Uctl9_s9
```