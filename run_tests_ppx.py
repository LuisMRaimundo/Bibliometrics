import sys, os
sys.path.insert(0, os.path.dirname(__file__))  # garante que o diretório atual entra no PYTHONPATH

import pandas as pd, numpy as np
from metrics.percentiles import compute_ppx, _pp_col_name

errs = 0
def check(cond, msg):
    global errs
    if not cond:
        print("FAIL:", msg); errs += 1

check(_pp_col_name(0.90) == "pp10", "pp_col_name 0.90")
check(_pp_col_name(0.99) == "pp1", "pp_col_name 0.99")
check(_pp_col_name(0.995) == "pp0.5", "pp_col_name 0.995")

df = pd.DataFrame({"year":[2020]*5+ [2021]*5, "field":["A"]*10, "score":[0,1,2,3,4, 10,20,30,40,50]})
out = compute_ppx(df, "score", by=["year","field"], p=0.80, ties=">=threshold")
thr_2020 = out.loc[out["year"]==2020, "ppx_threshold"].iloc[0]
thr_2021 = out.loc[out["year"]==2021, "ppx_threshold"].iloc[0]
check(abs(thr_2020-3.2)<1e-9, "thr_2020 80th")
check(abs(thr_2021-42.0)<1e-9, "thr_2021 80th")
check(out.loc[(out["year"]==2020)&(out["score"]==4), "pp20"].iloc[0]==1, "flag 2020 score4")
check(out.loc[(out["year"]==2020)&(out["score"]==3), "pp20"].iloc[0]==0, "flag 2020 score3")

df2 = pd.DataFrame({"year":[2020]*5, "field":["A"]*5, "score":[1,2,3,4,5]})
out2 = compute_ppx(df2, "score", by=["year","field"], p=0.80, ties=">threshold")
check(out2["pp20"].sum()==1, "strict ties sum")
check(out2.loc[out2["score"]==5, "pp20"].iloc[0]==1, "strict ties winner")

df3 = pd.DataFrame({"year":[2020,2020,2021,2021], "field":["A","A","B","B"], "score":[np.nan, np.nan, 10, np.nan]})
out3 = compute_ppx(df3, "score", by=["year","field"], p=0.90)
check(out3.loc[(out3["year"]==2020)&(out3["field"]=="A"), "pp10"].sum()==0, "empty group flags 0")
check(out3.loc[(out3["year"]==2020)&(out3["field"]=="A"), "ppx_threshold"].isna().all(), "empty group thr NaN")
check(out3.loc[(out3["year"]==2021)&(out3["field"]=="B"), "pp10"].sum()==1, "single value flagged")

df4 = pd.DataFrame({"score":[0,1,2,3,4]})
out4 = compute_ppx(df4, "score", by=[], p=0.60)
check(out4["pp40"].sum()==2, "global thr count")
check(abs(out4["ppx_threshold"].iloc[0]-2.4)<1e-9, "global thr value")

print("Errors:", errs)
