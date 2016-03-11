# __________________________________________________________
# //////////////////////////////////////////////////////////
#
#    MODULE 3 - SCORING
# __________________________________________________________
# //////////////////////////////////////////////////////////
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pandasql import sqldf
import statsmodels.api as sm


# --- COMPUTING PREDICTORS AND TARGET VARIABLES ------------


# Load text file into local variable called 'data'
data = pd.read_table('purchases.txt', header = None)

# Add headers and interpret the last column as a date, extract year of purchase
data.columns = ['customer_id', 'purchase_amount', 'date_of_purchase']
data['date_of_purchase'] = pd.to_datetime(data.date_of_purchase)
data['year_of_purchase'] = pd.DatetimeIndex(data['date_of_purchase']).year
data['days_since'] = (pd.Timestamp('2016-01-01') - data['date_of_purchase']).dt.days

# Compute key marketing indicators using SQL language

# Compute RFM variables as of a year ago
customers_2014 = sqldf("SELECT customer_id, MIN(days_since) - 365 AS 'recency', MAX(days_since) - 365 AS 'first_purchase', COUNT(*) AS 'frequency', AVG(purchase_amount) AS 'avg_amount', MAX(purchase_amount) AS 'max_amount' FROM data WHERE days_since > 365 GROUP BY 1", globals())

# Compute revenues generated by customers in 2015
revenue_2015 = sqldf("SELECT customer_id, SUM(purchase_amount) AS 'revenue_2015' FROM data WHERE year_of_purchase = 2015 GROUP BY 1", globals())

# Merge 2015 customers and 2015 revenue
in_sample = pd.merge(customers_2014, revenue_2015, how='left')
in_sample.revenue_2015 = in_sample.revenue_2015.replace(np.nan, 0)
in_sample['active_2015'] = np.where(in_sample['revenue_2015'] > 0, 1, 0)

# Display calibration (in-sample) data
in_sample.head()
in_sample.describe()


# --- CALIBRATE THE MODELS ---------------------------------


# Calibrate probability model
prob_model = sm.Logit.from_formula(b'active_2015 ~ recency + first_purchase + frequency + avg_amount + max_amount', in_sample)
prob_model_fit = prob_model.fit()
coef = prob_model_fit.params
std = prob_model_fit.bse
print(coef)
print(std)
print(coef / std)
#Logit gives same results as MNLogit. No need to use MNLogit here as we have binary data. MNLogit only messes up the prediction further down.

# For the monetary model, select only those who made a purchase
z = in_sample[in_sample.active_2015 == 1].index.tolist()
in_sample.loc[z].head()
in_sample.loc[z].describe()

# Calibrate the monetary model (version 1)
amount_model = sm.OLS.from_formula(b'revenue_2015 ~ avg_amount + max_amount', in_sample.loc[z])
amount_model_fit = amount_model.fit()
amount_model_fit.summary()

# Plot the results of the monetary model
plt.scatter(in_sample.loc[z].revenue_2015, amount_model_fit.fittedvalues)

# Re-calibrate the monetary model, using a log-transform (version 2)
amount_model = sm.OLS.from_formula(b'log(revenue_2015) ~ log(avg_amount) + log(max_amount)', in_sample.loc[z])
amount_model_fit = amount_model.fit()
amount_model_fit.summary()
amount.model = lm(formula = log(revenue_2015) ~ log(avg_amount) + log(max_amount), data = in_sample[z, ])
summary(amount.model)

# Plot the results of this new monetary model
plt.scatter(log(in_sample.loc[z].revenue_2015), amount_model_fit.fittedvalues)


# --- APPLY THE MODELS TO TODAY'S DATA ---------------------


# Compute RFM variables as of today
customers_2015 = sqldf("SELECT customer_id, MIN(days_since) AS 'recency', MAX(days_since) AS 'first_purchase', COUNT(*) AS 'frequency', AVG(purchase_amount) AS 'avg_amount', MAX(purchase_amount) AS 'max_amount' FROM data GROUP BY 1", globals())

# Predict the target variables based on today's data
customers_2015['prob_predicted'] = prob_model_fit.predict(customers_2015)
customers_2015['revenue_predicted'] = exp(amount_model_fit.predict(customers_2015))
customers_2015['score_predicted'] = customers_2015['prob_predicted'] * customers_2015['revenue_predicted']
customers_2015.prob_predicted.describe()
customers_2015.revenue_predicted.describe()
customers_2015.score_predicted.describe()
customers_2015.score_predicted.hist(bins=20)


# How many customers have an expected revenue of more than $50
z = customers_2015[customers_2015.score_predicted > 50].index.tolist()
print(len(z))