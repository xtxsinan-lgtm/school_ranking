"""Pool UC source-school counts (CA high schools, fall 2021-2025) into one row per school.

UC blanks any cell with fewer than 3 students.  Where a school-year-campus has an App (or Adm) cell but
the Adm (or Enr) cell is missing, the true value is 0-2, so we impute 1 before pooling.
"""
import sys
import pandas as pd

EXPORT = sys.argv[1] if len(sys.argv) > 1 else "uc_export"
Y0, Y1 = 2021, 2025  # test-blind era, 5 cohorts

e = pd.read_csv(f"{EXPORT}/uc_ethnicity.csv.gz")
e = e[(e.ethnicity == "All") & e.fall_term.between(Y0, Y1)]
s = pd.read_csv(f"{EXPORT}/uc_schools.csv.gz")
s = s[s.school_type.str.startswith("California")]
e = e.merge(s[["ceeb"]], on="ceeb")

t = e.pivot_table(index=["ceeb", "fall_term", "campus"], columns="measure", values="count", aggfunc="sum")
t = t[["App", "Adm", "Enr"]]
t["Adm"] = t.Adm.where(t.Adm.notna(), t.App.notna() * 1.0).where(t.App.notna() | t.Adm.notna())
t["Enr"] = t.Enr.where(t.Enr.notna(), t.Adm.notna() * 1.0).where(t.Adm.notna() | t.Enr.notna())
t = t.reset_index()
p = t.groupby(["ceeb", "campus"])[["App", "Adm", "Enr"]].sum().reset_index()
w = p.pivot(index="ceeb", columns="campus")
w.columns = [f"{m}_{c.replace(' ', '')}" for m, c in w.columns]
w = w.fillna(0).reset_index().merge(s[["ceeb", "name", "city", "school_type", "school_id"]], on="ceeb")
w.to_csv("data/uc_school_pooled_2021_2025.csv", index=False)
print(w.shape)
