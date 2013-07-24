import matplotlib
#matplotlib.use('Agg')
import  ephem
import  math
import  sys
from    utils import *
import  numpy as np
from    datetime import datetime
import  time as itime
import  matplotlib.pyplot as plt
from    matplotlib.colors import LogNorm
import  cPickle as pickle
import  pytz
import  heapq
utc_tz  = pytz.utc
tz_used = pytz.timezone("US/Central")
font = {'size'   : 6}

matplotlib.rc('font', **font)
states=pickle.load(open('stateDB.pickle','r'))    
def getSun(stateID, currentTime, city=None):
    """Get the position of the sun at a given time and location.
    
    Parameters:
    stateID  -- A string abbreviation of the state name, ie "IL","AZ",etc..
    currentTime -- Local time with tzinfo = state time zone.
    city (optional) -- The City  (defaults to state capital if missing or not found in database).
    
    Returns:
    sin(altitude) (representing how much sunlight hits an area)
    """
        #Note:  altitude,azimuth are given in radians
    o = ephem.Observer()    
    stateID.capitalize()
    dateStamp=currentTime.astimezone(pytz.utc)
    
    if city is None:
        city=states[stateID]['capital']        
    else:
        try:
            city=states[stateID][city].capitalize()
        except:
            city=states[stateID]['capital'] 
            
    o.lat    = states[stateID][city][0]
    o.long   = states[stateID][city][1]
    o.date   = dateStamp
    sun = ephem.Sun(o)
    alt=sun.alt
    return math.sin(alt)

def get_periods(d, nobs, first_pred, which = "kwhs", skip_fun = (lambda x: False), wrap_around = False):
    """Get a collection of periods (e.g., weeks) from a building record.

    Parameters:
    d -- The building record.
    nobs -- The number (int) of observations for a single period (e.g., 168 for weeks).
    first_pred -- A function which, given a datetime object, returns True if it is the start of the period.
                  For example, first_pred returns True only when the argument is Sunday at Midnight.
    which -- A string representing which time series in the building record to use (defaults to "kwhs")
    skip_fun -- A function which takes a datetime object and returns True if that time should be skipped.
                For example, skip_fun may return True on weekends, to obtain only work weeks.
    wrap_around -- If True, the beginning part of the time series is placed at the end.
                   For example, if we're starting periods on Monday, but the first day in the time series 
                   is Thursday, then the first part (from Thrusday to Monday) will be moved to the end.

    Returns (pers, new_times):
         pers -- The values (e.g., kwhs) of the periods.
         new_times -- The times (datetime objects) associated with the values.
    """
    times                  = d["times"]
    series, series_oriflag = d[which]
    
    additional_mask = np.array([skip_fun(t) for t in times])
    new_mask = np.logical_or((~series_oriflag), additional_mask)
    masked_series = np.ma.array(series, mask = new_mask)
    
    first = 0
    for ind, t in enumerate(times):
        if first_pred(t):
            first = ind
            break
    if wrap_around:
        pers      = np.ma.concatenate([masked_series[first:], masked_series[:first]])
        new_times = np.ma.concatenate([times[first:], times[:first]])
    else:
        pers      = masked_series[first:]
        new_times = times[first:]

    residue = len(pers) % nobs
    if residue != 0:
        pers      = pers[:-residue]#trim off extra
        new_times = new_times[:-residue]

    pers      = pers.reshape(-1, nobs)
    new_times = new_times.reshape(-1, nobs)
    return pers, new_times


def make_text_fig(d, textfig):
    """Show the static information from the building record in a given axis.

    Parameters:
    d -- The building record.
    textfig -- The axis to hold the figure.
    """
    bid                  = d["bid"]
    naics                = d["naics"]
    btype                = d["btype"]
    times                = d["times"]
    kwhs, kwhs_oriflag   = d["kwhs"]
    temps, temps_oriflag = d["temps"]
    naics_map, desc = qload("NAICS.pkl")
    if naics in naics_map:
        naics_str = naics_map[naics]
        naics_str = " (" + naics_str.lstrip().rstrip() + ")"
    else:
        naics_str = ""

    toPrint =  "ID:\n   "   + str(bid)\
        + "\nNaics:\n   "     + str(naics) + naics_str\
        + "\nType:\n   "    + str(btype)\
        + "\nAverage Hourly Energy Usage:\n    " + str(np.round(np.average(kwhs), 2)) + "kw"\
        + "\nMin:\n    "    + str(np.round(np.min(kwhs), 2))\
        + "\nMax:\n    "    + str(np.round(np.max(kwhs), 2))\
        + "\nTotal:\n     " + str(np.round(np.sum(kwhs)/1000.0, 2)) + "gwh"
    textfig.text(0.05, .95,toPrint , fontsize=12, ha='left', va='top')
    
    textfig.set_xticks([])
    textfig.set_yticks([])
    

def make_temp_vs_time_fig(d, tvt):
    """Show temperature as a function of time in a given axis.

    Parameters:
    d -- The building record.
    tvt -- The axis to hold the figure.
    """
    times                = d["times"]
    temps, temps_oriflag = d["temps"]
    
    tvt.plot(   times[temps_oriflag] , temps[temps_oriflag] , c = "blue")
    tvt.scatter(times[~temps_oriflag], temps[~temps_oriflag], lw = 0,  c = "red")
    tvt.scatter(times[~temps_oriflag], [0 for x in temps[~temps_oriflag]], lw = 0,  c = "red", s = 1)

    tvt.set_title("Temperature Over Time")
    tvt.set_ylabel("Temperature")
    
    labels = tvt.get_xticklabels() 
    for label in labels: 
        label.set_rotation(30) 
        

def make_kwhs_vs_time_fig(d, tvk):
    """Show kwhs as a function of time in a given axis.

    Parameters:
    d -- The building record.
    tvk -- The axis to hold the figure.
    """
    times                = d["times"]
    kwhs, kwhs_oriflag   = d["kwhs"]

    tvk.plot(times[kwhs_oriflag], kwhs[kwhs_oriflag], c = "blue", label = "Energy Usage")
    tvk.scatter(times[~kwhs_oriflag], kwhs[~kwhs_oriflag], c = "red", lw = 0, label = "Imputed Values")
    tvk.scatter(times[~kwhs_oriflag], [0 for x in kwhs[~kwhs_oriflag]], c = "red", lw = 0, s = 1)
    ori_kwhs    = kwhs[kwhs_oriflag]
    per_95_kwhs = np.percentile(ori_kwhs, 95)
    per_5_kwhs  = np.percentile(ori_kwhs, 5)
    tvk.axhline(y = per_95_kwhs, c = "red", ls = "dashed", label = "95th Percentile")
    tvk.axhline(y = per_5_kwhs,  c = "black", ls = "dashed", label = "5th Percentile")
    tvk.set_title("Energy Usage Over Time")
    tvk.legend()
    tvk.set_ylabel("kwhs")
    labels = tvk.get_xticklabels() 
    for label in labels: 
        label.set_rotation(30) 


def make_freqs_fig(d, freqs):
    """Show kwhs in the frequency domain (via the DFT).
       Note: This function requires data from (all of) 2011.

    Parameters:
    d -- The building record.
    freqs -- The axis to hold the figure.
    """
    times                = d["times"]
    kwhs, kwhs_oriflag   = d["kwhs"]
    temps, temps_oriflag = d["temps"]

    start_time  = "01/01/2011 00:00:00"
    end_time    = "01/01/2012 00:00:00"
    start_ts    = int(itime.mktime(datetime.strptime(start_time, "%m/%d/%Y %H:%M:%S").timetuple()))
    end_ts      = int(itime.mktime(datetime.strptime(end_time, "%m/%d/%Y %H:%M:%S").timetuple()))
    
    all_times = range(start_ts, end_ts, 3600)
    num_times = len(all_times)
    
    a     = np.fft.fft(kwhs)
    half  = int(num_times + 1)/2
    a     = a[0:half +1]
    a[0]  = 0 #drop constant part of signal
    reals = [x.real for x in a]
    imags = [x.imag for x in a]
    freqs.set_xlabel("Period (h)")
    freqs.set_ylabel("Magnitude")
    freqs.plot(reals, label = "Real", alpha = 0.9)
    freqs.plot(imags, label = "Imaginary", alpha = 0.8)
    
    highlighted_periods =  np.array([3, 6, 12, 24, 168])
    highlighted_freqs   = float(num_times) / highlighted_periods
    highlighted_labels  = [str(x) for x in highlighted_periods]
    freqs.set_xticks(highlighted_freqs)          
    freqs.set_xticklabels(highlighted_labels)
    
    freqs.legend()
    freqs.set_title("Energy usage over time in the frequency domain")
    labels = freqs.get_xticklabels() 
    for label in labels: 
        label.set_rotation(30) 


def make_temp_vs_kwh_fig(d, tmpsvk):
    """Show a 2d-histogram of temperatures vs kwhs in a given axis.
    
    Parameters:
    d -- The building record.
    tmpsvk -- The axis to hold the figure.
    """
    kwhs, kwhs_oriflag   = d["kwhs"]
    temps, temps_oriflag = d["temps"]

    both_ori = np.logical_and(temps_oriflag, kwhs_oriflag)
    tmpsvk.hist2d(temps[both_ori], kwhs[both_ori], bins = 50, norm = LogNorm())
    
    tmpsvk.set_title("Temperature vs Energy Usage")
    tmpsvk.set_xlabel("Temperature")
    tmpsvk.set_ylabel("kwh")
    tmpsvk.grid(True)

    
def make_avg_day_fig(d, avgday):
    """Show the average day in a given axis.
       Note: imputed values are ignored.

    Parameters:
    d -- The building record.
    avgday -- The axis to hold the figure.
    """

    is_midnight     = (lambda x: x.hour == 0)
    days, new_times = get_periods(d, 24, is_midnight, "kwhs")

    skip_weekdays   = (lambda x: x.weekday() < 5)
    weekends, _     = get_periods(d, 24, is_midnight, "kwhs", skip_weekdays)

    skip_weekend    = (lambda x: x.weekday() >= 5)
    weekdays, _     = get_periods(d, 24, is_midnight, "kwhs", skip_weekend)

    avg_weekend     = np.ma.average(weekends, axis = 0)
    avg_weekday     = np.ma.average(weekdays, axis = 0)
    avg_day         = np.ma.average(days, axis = 0)
 
    std_weekend     = np.ma.std(weekends, axis = 0)
    std_weekday     = np.ma.std(weekdays, axis = 0)
    std_day         = np.ma.std(days, axis = 0)

    avgday.errorbar(np.arange(24), avg_weekend, yerr =std_weekend, label = "Weekend")
    avgday.errorbar(np.arange(24), avg_weekday, yerr =std_weekday, label = "Weekday")
    avgday.errorbar(np.arange(24), avg_day,     yerr =std_day,     label = "Day")

    avgday.set_title("Average Day")
    avgday.set_ylabel("Energy Usage (kwh)")
    avgday.set_xlim(-0.5, 24.5)
    avgday.set_xticks(range(0, 24, 4))
    avgday.grid(True)
    avgday.legend()


def make_avg_week_fig(d, avgweek):
    """Show the average week in a given axis.
       Note: imputed values are ignored.

    Parameters:
    d -- The building record.
    avgweek -- The axis to hold the figure.
    """

    is_sunday_start  = (lambda x: x.weekday() == 6 and x.hour == 0)
    weeks, new_times = get_periods(d, 168, is_sunday_start, "kwhs")

    avg_week  = np.ma.average(weeks, axis = 0)
    std_week  = np.ma.std(weeks, axis = 0)

    avgweek.errorbar(np.arange(168), avg_week, yerr =std_week, label = "Energy Usage", errorevery = 6)

    avgweek.set_title("Average Week")
    avgweek.set_ylabel("Energy Usage (kwh)")
    avgweek.set_xlim(-0.5, 24.5)
    avgweek.set_xticks(range(0, 169, 24))
    avgweek.set_xticklabels(["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
    labels = avgweek.get_xticklabels() 
    for label in labels: 
        label.set_rotation(30) 

    avgweek.grid(True)
    avgweek.legend()


def make_hist_fig(d, hist):
    """Show a histogram of hourly energy usage.
       Note: imputed values are ignored.

    Parameters:
    d -- The building record.
    hist -- The axis to hold the figure.
    """
    kwhs, kwhs_oriflag   = d["kwhs"]
    
    hist.hist(kwhs[kwhs_oriflag], bins = 50)
    hist.set_title("Histogram of Energy Usage")
    hist.set_ylabel("kwhs")


def gen_peaks(d, num_peaks = 3):
    """A generatore that yields the index of the highest peaks.
       
    Parameters:
    d -- The building record.
    num_peaks -- The number of peaks to be yielded.
    """
    kwhs, kwhs_oriflag   = d["kwhs"]
    
    inds = np.argsort(kwhs)[-num_peaks:]
    for ind in inds:
        yield ind


def make_peak_fig(d, ax, ind):
    """Show the 24-hour period around the time at index ind.

    Parameters:
    d -- The building record.
    ax -- The axis to hold the figure.
    ind -- The index of the time to display.
    """


    times                = d["times"]
    kwhs, kwhs_oriflag   = d["kwhs"]
 
    highest_date = times[ind]
    highest_val  = kwhs[ind]
    leftmost  = max(0, ind-12)
    rightmost = min(len(kwhs), ind+12)
    
    make_interval_plot(d, ax, leftmost, rightmost)
    


def make_kwh_vs_sun_fig(d, ax):
    """Show a 2d-histogram of kwhs vs the position of the sun in a given axis.
       Note: Imputed values are ignored.

    Parameters:
    d -- The building record.
    ax -- The axis to hold the figure.
    """



   
    bid                  = d["bid"]
    naics                = d["naics"]
    btype                = d["btype"]
    times                = d["times"]
    kwhs, kwhs_oriflag   = d["kwhs"]
    temps, temps_oriflag = d["temps"]

    sun_pos = np.array([max(-100, getSun("IL", t)) for t in times[kwhs_oriflag]])
    #ax.hist2d(kwhs[kwhs_oriflag], sun_pos, bins = 50, norm = LogNorm())
    ax.hist2d(sun_pos, kwhs[kwhs_oriflag], bins = 50, norm = LogNorm())
    
    ax.set_title("Energy Usage vs sunlight")
    ax.set_xlabel("Sunlight")
    ax.set_ylabel("kwh")
    ax.grid(True)


def make_monthly_usage_fig(d, ax):
    """Show a barchart with the totaly electricy usage by month.
    
    Parameters:
    d -- The building record.
    ax-- The axis to hold the figure.
    """
    times                = d["times"]
    kwhs, kwhs_oriflag   = d["kwhs"]

    month_breaks = [ind for ind, t in enumerate(times) if t.day == 1 and t.hour == 0]

    zeroed_kwhs  = [k if flg else 0 for k, flg in zip(kwhs, kwhs_oriflag)] 
    month_totals = [np.sum(zeroed_kwhs[s:e]) for s, e in zip(month_breaks, month_breaks[1:] + [-1])]
    
    ax.bar([times[i] for i in month_breaks], month_totals, width = 10)
    labels = ax.get_xticklabels() 
    for label in labels: 
        label.set_rotation(30) 
    ax.set_title("Monthly Energy Usage")
    ax.set_ylabel("kwhs")
    ax.grid(True)


def gen_strange_pers(d, num_pers = 3, period = "day"):
    """A generator which yields the strangest period (day or week).

    Parameters:
    d -- The building record.
    num_pers -- The number of periods to be yieled (one at a time).
    period -- A string, either "day" or "week".
    """
    kwhs, kwhs_oriflag = d["kwhs"]
    times = d["times"]
    if period == "day":
        first_pred = (lambda x: x.hour == 0)
    elif period == "week":
        first_pred = (lambda x: x.weekday() == 0 and x.hour == 0)
    else:
        print "period must be 'day' or 'week'."
        return
    num_per_period = 24 if period == "day" else 168
    pers, new_times = get_periods(d, num_per_period, first_pred, "kwhs")
    temp_pers, _ = get_periods(d, num_per_period, first_pred, which = "temps")

    avg_per         = np.average(pers, axis=0)
    weirdness       = []
    totals          = []
    
    standardize = True
    if standardize:
        avg_per = avg_per - np.min(avg_per)
        avg_per = avg_per / np.max(avg_per)

    for per in pers:
        if standardize:
            per = per - np.min(per)
            per = per / np.max(per)

        dist = np.average(np.abs(per - avg_per))        
        weirdness.append(dist)
    inds = np.argsort(weirdness)[-num_pers:][::-1]
    for ind in inds:
        left_side  = np.argmax(times == new_times[ind][0])#hackish, but oh well
        right_side = np.argmax(times == new_times[ind][-1])#hackish, but oh well
 

        yield left_side, right_side

#        vals = pers[ind]
#        times = new_times[ind]
#        temps = temp_pers[ind]
        

#        yield vals, temps, times
        

def make_strange_per_fig(d, ax, per):
    """Creates a plot of the period yieled from get_strange_pers.

    Parameters:
    d -- The building record.
    ax -- The axis to hold the figure.
    per -- The period yieled from get_strange_pers.
    """

    if len(per) == 2:
        start, end = per
        make_interval_plot(d, ax, start, end)
    else:
        kvals, tvals, new_times = per
        ax.plot(new_times, kvals, label = "kwhs")
        ax.plot(new_times, tvals, label = "temperature")
    
        ax.set_title("Beginning " + new_times[0].strftime("%m/%d/%Y"))
        ax.set_ylabel("kwhs/temperature")
        labels = ax.get_xticklabels() 
        for label in labels: 
            label.set_rotation(30) 
   
        ax.grid(True)
        ax.legend()

def make_extreme_days_figs(d, axhigh, axlow):
    """Show the extreme high and extreme low days (in terms of electricity usage).
    
    Parameters:
    d -- The building recorod.
    axhigh -- The axis to hold the extreme-high figure.
    axlow -- The axis to hold the extreme-low figure.
    """
    is_midnight     = (lambda x: x.hour == 0)
    days, new_times = get_periods(d, 24, is_midnight, "kwhs")
    avg_day         = np.average(days, axis=0)
    weirdness       = []
    totals          = []
    times           = d["times"]

    for day in days:
        total = np.sum(day)
        totals.append(total)
        dist = np.average(np.abs(day - avg_day))
        weirdness.append(dist)
    ind = np.argmax(totals)
    highest_day = new_times[ind][0]
   
    left_side  = np.argmax(times == new_times[ind][0])#hackish, but oh well
    right_side = np.argmax(times == new_times[ind][-1])#hackish, but oh well
    make_interval_plot(d, axhigh, left_side, right_side)
    #    axhigh.plot(new_times[ind], days[ind])
    axhigh.set_title("Highest Day\n" + highest_day.strftime("%m/%d/%Y"))
   
    ind = np.argmin(totals)
    lowest_day = new_times[ind][0]
    left_side  = np.argmax(times == new_times[ind][0])#hackish, but oh well
    right_side = np.argmax(times == new_times[ind][-1])#hackish, but oh well
    make_interval_plot(d, axlow, left_side, right_side)

    axlow.set_title("Lowest Day\n" + lowest_day.strftime("%m/%d/%Y"))


def gen_over_thresh(d, thresh):
    """A generatore that yields the times where the energy usage was above some threshold.
    
    Parameters:
    d -- The building record.
    thresh -- The threshold.

    Returns:
    TODO
    """
    times                = d["times"]
    kwhs, kwhs_oriflag   = d["kwhs"]
    temps, temps_oriflag = d["temps"]

    #right now, just assume you start and end below thresh
    left_sides   = [ind for ind in range(len(kwhs)-1) if kwhs[ind] <= thresh and kwhs[ind+1] > thresh]
    right_sides  = [ind for ind in range(len(kwhs)-1) if kwhs[ind] > thresh and kwhs[ind+1] <= thresh]
    periods = zip(left_sides, right_sides)

    for ls, rs in periods:
        new_left_side  = max(0, ls - 12)
        new_right_side = min(len(kwhs)-1, rs + 12)

        kvals  =  kwhs[new_left_side:new_right_side]
        ptimes = times[new_left_side:new_right_side]
        tvals  = temps[new_left_side:new_right_side]

        yield new_left_side, new_right_side
        #yield kvals, tvals,  ptimes


def get_times_of_highest_change(d, num_times, direction = "increase"):
    """Returns the indices where the highest increase in electricity usage occured.
    Note the indices returned are for just before the spikes occured (as opposed to just after).

    Parameters:
    d -- The building record.
    num_times -- The number of times to be returned.
    direction -- Either "increase" (default) or "decrease"
    """
    kwhs, kwhs_oriflag = d["kwhs"]
    times = d["times"]
    first_deriv = kwhs[1:] - kwhs[:-1]

    inds = np.argsort(first_deriv)

    if direction == "increase":
        inds = inds[-num_times:][::-1]
    else:
        inds = inds[:num_times]

    return inds


def make_interval_plot(d, ax, start, end, show_temps = True, show_sun = True, show_weekends = True):

    times                = d["times"]
    kwhs, kwhs_oriflag   = d["kwhs"]
    temps, temps_oriflag = d["temps"]    

    kwhs          = kwhs[start:end]
    kwhs_oriflag  = kwhs_oriflag[start:end]
    temps         = temps[start:end]
    temps_oriflag = temps_oriflag[start:end]
    times         = times[start:end]

    lns1 = ax.plot(times, kwhs, label = "kwhs")
    ax.set_ylabel("kwh")

    suns = np.array([max(0, getSun("IL", x)) for x in times])
    sun_ax = ax.twinx()
    lns2 = sun_ax.plot(times, suns, label = "Sunlight", c = "purple", alpha = 0.3, ls = "dashed")

    sun_ax.set_ylim((-.5, 1))
    sun_ax.set_yticks([])


    weather_ax = sun_ax.twinx()
    weather_ax.set_ylabel("Temperature")
    lns3 = weather_ax.plot(times, temps, label = "Temperature", c = "red", alpha = 0.4)
        
    lns = lns1+lns2+lns3
    labs = [l.get_label() for l in lns]
    weather_ax.legend(lns, labs, loc=0)
    
    
    ax.grid(True)

    labels = ax.get_xticklabels() 
    for label in labels: 
        label.set_rotation(30) 

def plot_it(d):
    """PLOT IT!"""
    bid = d["bid"]
    fig = plt.figure(figsize = (20, 20))
    
    nrows    = 4
    ncols    = 3
    tmpsvk   = fig.add_subplot(nrows, ncols, 3)
    textfig  = fig.add_subplot(nrows, ncols, 2)
    tvt      = fig.add_subplot(nrows, 1, 4)
    tvk      = fig.add_subplot(nrows, 1, 3)
    avgday   = fig.add_subplot(nrows, 2, 3)
    avgweek  = fig.add_subplot(nrows, 2, 4)
    #freqs    = fig.add_subplot(nrows, ncols, 1)
    hist     = fig.add_subplot(nrows, ncols, 1)
    
    make_text_fig(d, textfig)
    make_temp_vs_time_fig(d, tvt)
    make_kwhs_vs_time_fig(d, tvk)
    #make_freqs_fig(d, freqs)
    make_hist_fig(d, hist)
    make_temp_vs_kwh_fig(d, tmpsvk)
    make_avg_day_fig(d, avgday)
    make_avg_week_fig(d, avgweek)
    plt.subplots_adjust(hspace = .35)
    plt.savefig(fig_loc + "fig_" + str(bid) + "_2011.png")
    plt.clf()
    plt.close()
    

def multi_plot(d):
    size = (10, 10)
    #General/global figure
    g_fig = plt.figure(figsize = size)
    g_text    = g_fig.add_subplot(2, 2, 1)
    g_hist    = g_fig.add_subplot(2, 2, 2)
    g_totals  = g_fig.add_subplot(2, 1, 2)

    make_text_fig(d, g_text)
    make_hist_fig(d, g_hist)
    make_monthly_usage_fig(d, g_totals)
    
    #Normalness figure
    n_fig = plt.figure(figsize = size)
    n_avgday  = n_fig.add_subplot(2, 2, 1)
    n_avgweek = n_fig.add_subplot(2, 2, 2)
    n_vstemp  = n_fig.add_subplot(2, 2, 3)
    n_vssun   = n_fig.add_subplot(2, 2, 4)

    make_avg_day_fig(d, n_avgday)
    make_avg_week_fig(d, n_avgweek)
    make_temp_vs_kwh_fig(d, n_vstemp)
    make_kwh_vs_sun_fig(d, n_vssun)
    
    #Appendix figure
    a_fig = plt.figure(figsize = size)
    a_temps    = a_fig.add_subplot(3, 1, 1)
    a_kwhs     = a_fig.add_subplot(3, 1, 2)
    a_freqs    = a_fig.add_subplot(3, 1, 3)
    
    make_temp_vs_time_fig(d, a_temps)
    make_kwhs_vs_time_fig(d, a_kwhs)
    make_freqs_fig(d, a_freqs)

    #outliers 
    outliers = plt.figure(figsize = size)
    avg_day = outliers.add_subplot(5, 2, 1)
    make_avg_day_fig(d, avg_day)

    days = gen_strange_pers(d, 4, period = "day")
    for i, p in enumerate(days):
        day_fig = outliers.add_subplot(5, 2, 2*(i + 2)-1)
        make_strange_per_fig(d, day_fig, p)

    avg_week = outliers.add_subplot(5, 2, 2)
    make_avg_week_fig(d, avg_week)

    weeks = gen_strange_pers(d, 4, period = "week")
    for i, p in enumerate(weeks):
        week_fig = outliers.add_subplot(5, 2, 2*(i + 2))
        make_strange_per_fig(d, week_fig, p)

    #overthresh
    overthresh = plt.figure(figsize = size)
    kwhs, kwhs_oriflag = d["kwhs"]
    thresh = np.percentile(kwhs[kwhs_oriflag], 99)
    overtimes = gen_over_thresh(d, thresh)
    
    for i, p in enumerate(overtimes):
        if i >= 9: break
        over_fig = overthresh.add_subplot(3, 3, i + 1)
        make_strange_per_fig(d, over_fig, p)

    #spikes

    times = d["times"]
    spikes = plt.figure(figsize = size)
    num_times = 4 
    inds = get_times_of_highest_change(d, num_times, direction = "increase")
    for i, ind in enumerate(inds):
        left_side  = max(0,          ind-12)
        right_side = min(len(times), ind+12)
        ax = spikes.add_subplot(num_times, 1, i+1)
        make_interval_plot(d, ax, left_side, right_side)
        ax.set_title("Spike at " + times[ind].strftime("%m/%d/%y %H:%M:%S"))

 
    #extreme days
    extremedays = plt.figure(figsize = size)
    axavg = extremedays.add_subplot(3, 1, 1)
    axhigh = extremedays.add_subplot(3, 1, 2)
    axlow = extremedays.add_subplot(3, 1, 3)
    make_avg_day_fig(d, axavg)
    make_extreme_days_figs(d, axhigh, axlow)


    plt.subplots_adjust(hspace = .55)
    plt.show()



if __name__ == "__main__":
    #data, desc = qload("agentis_b_records_2011_updated_small.pkl")
    #data, desc = qload("agentis_b_records_2011_updated.pkl")
    #data, desc = qload("agentis_oneyear_19870_updated.pkl")
    #data, desc = qload("agentis_oneyear_18400_updated.pkl")
    #data, desc = qload("agentis_oneyear_21143_updated.pkl")
    data, desc = qload("agentis_oneyear_22891_updated.pkl")
    data = [data]
    sys.stdout.flush()
    #data = [data[-1]]
    print "Data desc:", desc
    print "Number of points:", len(data)
    print "vals for point 0:", len(data[0]["times"])
    print "\n"
    for ind, d in enumerate(data):
        multi_plot(d)
        #fig = plt.figure(figsize = (10, 10))
        #ax = fig.add_subplot(1, 1, 1)
        #make_interval_plot(d, ax, 500, 500+168)
        plt.show()
        #exit()
        #plot_it(d)
        #bid = d["bid"]
        #print str(ind), ": plotted something..."
        sys.stdout.flush()
        
        
