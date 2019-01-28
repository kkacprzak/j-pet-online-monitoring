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

def __makeArrays(data):

    times = np.array([dp.parse(line[2]) for line in data])

    temps = []
    for i in range(10):
        temps.append(np.array([line[8+i] for line in data]))

    pressures = []    
    for i in range(3):
        pressures.append(np.array([line[3+i] for line in data]))

    humidities = []    
    for i in range(2):
        humidities.append(np.array([line[6+i] for line in data]))

    return (times, temps, pressures, humidities)


##########################################################################
# Create a single figure and write to disk                               #
##########################################################################
def __makePlot(generator, arrs, outpath, filename, ylabel):

    fmt = dates.DateFormatter("%d %b %H:%M")
    fig, ax = plt.subplots()
    ax.xaxis.set_major_locator(dates.HourLocator())
    ax.xaxis.set_minor_locator(dates.MinuteLocator(interval=30))
    ax.xaxis.set_major_formatter(fmt)    
    ax.set_ylabel(ylabel)
    
    plots = generator(arrs, ax)

    # Put a legend above current axis
    ax.legend(
        bbox_to_anchor=(0,1.02,1,0.2), loc="lower left",
                mode="expand", borderaxespad=0, ncol=len(plots)/2)

    fig.autofmt_xdate()
    ax.grid(True)

    plt.tight_layout()
    plt.show()
    fig.savefig(outpath + filename)
    plt.close(fig)
    
def plotMeteoStuff(data, outpath):
    
    arrays = __makeArrays(data)

    ##################################################################
    # plot temperatures                                              #
    ##################################################################
    gen = lambda arrs, axis: [axis.plot(arrs[0], arrs[1][i], label='T'+str(i)) for i in range(10)]
    __makePlot(gen, arrays, 'plots/', 'temp.png', 'C')
    
    ##################################################################
    # plot vacuum system pressures                                   #
    ##################################################################
    def pressures_generator(arrs, axis):
        plots = []
        plots.append(axis.plot(arrs[0], arrs[2][0], 'b', label='vacuum system pressures'))
        axis2 = axis.twinx()
        plots.append(axis2.plot(arrs[0], arrs[2][1], 'r', label='P1'))
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

if __name__ == "__main__":

    data = [(1, u'2019-01-16T00:54:17', u'2019-01-16T00:55:13.605581', 97892.0, None, None, 14.7, 31.1, 23.9, 21.9, 20.6, 20.3, 28.9, 20.2, 19.7, 21.6, 24.6, 22.0, u'zyx'), (2, u'2019-01-16T00:56:22', u'2019-01-16T00:57:19.140221', 97892.0, None, None, 14.8, 31.5, 23.9, 21.8, 20.6, 20.2, 28.9, 20.2, 19.7, 21.6, 24.5, 22.0, u'zyx'), (3, u'2019-01-16T09:46:51', u'2019-01-16T09:47:18.514406', 98379.0, None, None, 14.8, 31.2, 23.9, 21.7, 20.7, 20.3, 28.7, 20.2, 19.7, 21.6, 24.5, 21.9, u'zyx'), (4, u'2019-01-16T09:46:51', u'2019-01-16T09:47:20.583187', 98379.0, None, None, 14.8, 31.2, 23.9, 21.7, 20.7, 20.3, 28.7, 20.2, 19.7, 21.6, 24.5, 21.9, u'zyx'), (5, u'2019-01-16T09:46:56', u'2019-01-16T09:47:22.648310', 98379.0, None, None, 14.8, 31.2, 23.9, 21.7, 20.7, 20.3, 28.7, 20.2, 19.7, 21.6, 24.5, 21.9, u'zyx'), (6, u'2019-01-16T09:46:56', u'2019-01-16T09:47:24.707288', 98379.0, None, None, 14.8, 31.2, 23.9, 21.7, 20.7, 20.3, 28.7, 20.2, 19.7, 21.6, 24.5, 21.9, u'zyx'), (7, u'2019-01-16T09:46:56', u'2019-01-16T09:47:26.782534', 98379.0, None, None, 14.8, 31.2, 23.9, 21.7, 20.7, 20.3, 28.7, 20.2, 19.7, 21.6, 24.5, 21.9, u'zyx'), (8, u'2019-01-16T09:47:01', u'2019-01-16T09:47:28.840617', 98375.0, None, None, 15.0, 31.2, 23.9, 21.7, 20.7, 20.3, 28.7, 20.2, 19.7, 21.6, 24.5, 21.9, u'zyx'), (9, u'2019-01-16T09:47:01', u'2019-01-16T09:47:30.948731', 98375.0, None, None, 15.0, 31.2, 23.9, 21.7, 20.7, 20.3, 28.7, 20.2, 19.7, 21.6, 24.5, 21.9, u'zyx'), (10, u'2019-01-16T09:47:06', u'2019-01-16T09:47:33.006983', 98380.0, None, None, 14.9, 31.3, 23.9, 21.7, 20.7, 20.3, 28.6, 20.2, 19.7, 21.6, 24.4, 21.9, u'zyx'), (11, u'2019-01-16T09:47:06', u'2019-01-16T09:47:35.065017', 98380.0, None, None, 14.9, 31.3, 23.9, 21.7, 20.7, 20.3, 28.6, 20.2, 19.7, 21.6, 24.4, 21.9, u'zyx'), (12, u'2019-01-16T09:47:06', u'2019-01-16T09:47:37.131628', 98380.0, None, None, 14.9, 31.3, 23.9, 21.7, 20.7, 20.3, 28.6, 20.2, 19.7, 21.6, 24.4, 21.9, u'zyx'), (13, u'2019-01-16T09:47:11', u'2019-01-16T09:47:39.198157', 98381.0, None, None, 15.0, 31.2, 23.9, 21.7, 20.7, 20.3, 28.6, 20.2, 19.7, 21.6, 24.4, 21.9, u'zyx'), (14, u'2019-01-16T09:47:11', u'2019-01-16T09:47:41.264574', 98381.0, None, None, 15.0, 31.2, 23.9, 21.7, 20.7, 20.3, 28.6, 20.2, 19.7, 21.6, 24.4, 21.9, u'zyx'), (15, u'2019-01-16T09:47:16', u'2019-01-16T09:47:43.331135', 98372.0, None, None, 15.0, 31.2, 23.9, 21.7, 20.7, 20.3, 28.6, 20.2, 19.7, 21.6, 24.4, 21.9, u'zyx'), (16, u'2019-01-16T09:47:16', u'2019-01-16T09:47:45.397617', 98372.0, None, None, 15.0, 31.2, 23.9, 21.7, 20.7, 20.3, 28.6, 20.2, 19.7, 21.6, 24.4, 21.9, u'zyx')]
    
    plotMeteoStuff(data, 'plots/')


