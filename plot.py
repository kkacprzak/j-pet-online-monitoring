from datetime import datetime, timedelta
import dateutil.parser as dp
import numpy as np
import matplotlib as mpl
mpl.use('Agg') 
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoLocator
from matplotlib import dates
import logging

logger = logging.getLogger('plotting')

def __validateNumber(num):
    if num is not None:
        return num
    else:
        return 0.0

def __makeArrays(data):

    data = list(data)

    times = np.array([dp.parse(entry['MEASUREMENT_TIME']) for entry in data])
    
    temps = [np.array([entry[label] for entry in data]) for label in ('T0', 'T1')]
    pressures = [np.array([entry[label] for entry in data]) for label in ('P_ATM', 'P1', 'P2')]
    humidities = [np.array([entry[label] for entry in data]) for label in ('HUM1', 'HUM2')]

    return (times, temps, pressures, humidities)


##########################################################################
# Create a single figure and write to disk                               #
##########################################################################
def __makePlot(generator, arrs, outpath, filename, ylabel):

    fmt = dates.DateFormatter("%d %b %H:%M")
    fig, ax = plt.subplots()
    ax.xaxis.set_major_locator(dates.HourLocator(interval=3))
    ax.xaxis.set_minor_locator(dates.MinuteLocator(interval=10))
    ax.xaxis.set_major_formatter(fmt)    
    ax.set_ylabel(ylabel)
    
    plots = generator(arrs, ax)

    # Put a legend above current axis
    ax.legend(
        bbox_to_anchor=(0,1.02,1,0.2), loc="lower left",
                mode="expand", borderaxespad=0, ncol=len(plots)//2)

    fig.autofmt_xdate()
    ax.grid(True)

    try:
        plt.tight_layout()
    except RuntimeError as err:
        logger.error("Failed to generate plots, skipping plitting this time. Reason: {}".format(str(err)))
        return
    plt.show()
    fig.savefig(outpath + filename)
    plt.close(fig)
    
def plotMeteoStuff(data, outpath):
    
    arrays = __makeArrays(data)

    ##################################################################
    # plot temperatures                                              #
    ##################################################################
    gen = lambda arrs, axis: [axis.plot(arrs[0], arrs[1][i], label='T'+str(i)) for i in range(2)]
    __makePlot(gen, arrays, 'plots/', 'temp.png', 'C')
    
    ##################################################################
    # plot vacuum system pressures                                   #
    ##################################################################
    def pressures_generator(arrs, axis):
        plots = []
        plots.append(axis.plot(arrs[0], arrs[2][1], 'b', label='vacuum system (P0 - after rotary pump, P1 - after turbo pump)'))
        axis2 = axis.twinx()
        axis2.xaxis.set_major_formatter(dates.DateFormatter("%d %b %H:%M"))    
        plots.append(axis2.plot(arrs[0], arrs[2][2], 'r', label='P1'))
        axis.tick_params('y', colors='b')
        axis.set_ylabel('P0 [Pa]', color='b')
        axis2.tick_params('y', colors='r')
        axis2.set_ylabel('P1 [Pa]', color='r')
        
        return plots
        
    __makePlot(pressures_generator, arrays, 'plots/', 'pressure.png', 'Pa')

    ######################################################################
    # plot atm pressure                                                  #
    ######################################################################
    gen = lambda arrs, axis: [axis.plot(arrs[0], arrs[2][0], label='P atm')]
    __makePlot(gen, arrays, 'plots/', 'patm.png', 'Pa')

    ######################################################################
    # plot humidities                                                    #
    ######################################################################
    gen = lambda arrs, axis: [axis.plot(arrs[0], arrs[3][i], label='Humidity '+str(i)) for i in range(2)]
    __makePlot(gen, arrays, 'plots/', 'humidities.png', '%')
    
    logger.debug("Plotting done.")

def plotEventCounts(data, outpath):

    data = list(data)

    gen = lambda arrs, axis: [axis.plot(arrs[0], arrs[1], label='Selected events per file')]
    times = np.array([dp.parse(entry['MEASUREMENT_TIME']) for entry in data])
    counts = np.array([__validateNumber(entry['EVENT_COUNTS']) for entry in data])
    __makePlot(gen, (times, counts), 'plots/', 'events.png', 'Events')

    gen = lambda arrs, axis: [axis.plot(arrs[0], arrs[1], label='Integrated events')]
    integrated_counts = np.array([__validateNumber(entry['EVENTS_SUM']) for entry in data])
    __makePlot(gen, (times, integrated_counts), 'plots/', 'integrated_events.png', 'Total events')

