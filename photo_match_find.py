import os       # os module
import sys
from sys import argv
import cv2      # openCV moudle
import logging  # logging module
import filetype # file type checking module
import random   # --
from progress.bar import IncrementalBar as ibar 
from progress.spinner import Spinner as sp
import json

'''This program is used to find similar photos
(ONLY PHOTOS, NOT FILES) which may have same aspect
ratio and or rotated or even resized to small but are not
cropped, transformed etc. Just copy the program
to the destined folder, run it there & look for the
file 'Result.txt'. The photo files are needed
to be in 'jpg' format

How to imporve accuracy or speed?

As said, you need to tradeoff one for another.
This program takes (ROW/sample factor) & (COLUMN/
sample factor) number of random pixels from 
images and compare to generate average.
A good photo match will return 2 or near to it as
average and anything around 10 or more is not a possible
match. Sometimes extremely similar photos returns average
near to 2. If you want more accuracy, try multiple
sample factors & threshold values. Choosing the Low
sample factor may yeild more accurate results but
will cost you more time.

Can I resume the progress?

    Yes. If you run this over a large collection
(say 1000s of images) you can interrupt (ctrl+C) whenever
you want or lets say the programs stopped due to
power failure or whatever reasons, simply run
the program again with the file 'masterListPopulated.json'
as 1st argument. It'll resume the progress & run from
where it was sopped. The said json file will be
created automatically whenever you run the program.
So it must be in the same folder where you did your last run.
And also, take a backup copy of the said file each time you
interrupt the program or atleast before starting resuming.

e.g. python3.8 <this_script.py> masterListPopulated.json

    This program will first generate files list along
with their location & run image comparison among them.
Incase if you want to run a fresh comparison instead
resuming the last state but want to skip the files
list generation process (assuming you've large
collection), you can use file 'masterList.json'
file instead for resuming arguemnt. This will skip files
list generation part but start a fresh image comparison
process.


Logging option:

If you encounter issues and want to debug, this program
has logging function which could be enabled by enabling
the logging flag 'log_flag' (setting it to 'True').
This will generate logs of info for each process & loops
and store it in the file 'LOGFILE.log'. But beware that it'll
generate huge number of log entries like 1000+ entries
for 50 images & also consumes time (to open/close file object).
So logging in the realtime conditions is not advised especially
over large number of collections. Take few set of samples in a
folder & run the program with logging option to do your 
debugging.
'''

# Sample factor. [for better accuracy, try more than one]
sam_fac = [100, 30] # previously [200, 100, 75, 15]

# threshold (list length must be equal to sample factor)
th = [3, 3] # previously [3, 3, 3.5, 4]
    
# Configuring logger
logging.basicConfig(filename='LOGFILE.log', \
                    format='%(levelname)s - %(asctime)s - %(message)s',\
                    filemode='w')

# Creating logging object & setting threshold level
lg = logging.getLogger()
lg.setLevel(logging.DEBUG)

# Logging flag
log_flag = False

# Progress resume flag
p_resume = False


def down():
    '''Function used to pring progress bars'''
    sys.stdout.write('\n')
    sys.stdout.flush()

def up():
    '''Function used to pring progress bars'''
    sys.stdout.write('\x1b[1A')
    sys.stdout.flush()
    

def a_ratio(a):
    '''Aspect ratio'''
    return round(a.shape[0] / a.shape[1], 2)


def ra_ratio(a):
    '''Reverse aspect ratio'''
    return round(a.shape[1] / a.shape[0], 2)


def diff(x, y):
    '''Difference'''
    return x - y if x > y else y - x


def diff_avg(a, b, sample_factor):
    
    '''Differece average
    assuming objects 'a',
    'b' have same resolution'''

    n = 0
    avg = 0
    row, col = a.shape[:2]    
    r = random.sample(range(0, row - 10), round(row / sample_factor))
    c = random.sample(range(0, col - 10), round(col / sample_factor))
    
    for i in r:
        for j in c:
            try:
                avg += diff(a[i, j], b[i, j])
                n += 1
            except IndexError:
                log_it('diff_avg(): IndexError! i = %d; j = %d; a.shape = (%d, %d); b.shape = (%d, %d)', i, j, a.shape[0], a.shape[1], b.shape[0], b.shape[1])
            
    return round(avg / n, 2)
        

def im_resize(image, width = None, height = None, inter = cv2.INTER_AREA):
    # initialize the dimensions of the image to be resized and
    # grab the image size
    # width = column; height = row
    dim = None
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    # check to see if the width is None
    if width is None:
        # calculate the ratio of the height and construct the
        # dimensions
        r = height / float(h)
        dim = (int(w * r), height)

    # otherwise, the height is None
    else:
        # calculate the ratio of the width and construct the
        # dimensions
        r = width / float(w)
        dim = (width, int(h * r))

    # resize the image
    resized = cv2.resize(image, dim, interpolation = inter)

    # return the resized image
    return resized


def image_compare(a, b):
    
    '''a, b are image objects assuming both
    have same resolution & aspect ratio. pixel
    comparison will be done with 180 rotated
    condition if needed.
        for better accuray, checking process
    is designed to match all sample factors
    & calculate the average'''
    
    loop_count = 0
    average_tot = 0
    th_tot = 0
    for x, y in [(sam_fac[i], th[i]) for i in range(len(th))]:
        # comparing images & calculating difference average
        average_tot += diff_avg(a, b, x)
        th_tot += y

    average_tot_0 = round(average_tot / len(sam_fac), 2)
        
    if average_tot_0 < round(th_tot / len(sam_fac), 2):
        return average_tot_0
    else:
        # creating 180' rotated object of 'b'
        ro180_b = cv2.rotate(b, cv2.ROTATE_180)
        loop_count = 0
        average_tot = 0
        th_tot = 0
        for x, y in [(sam_fac[i], th[i]) for i in range(len(th))]:
            # comparing images & calculating difference average
            average_tot += diff_avg(a, ro180_b, x)
            th_tot += y
            
        average_tot_180 = round(average_tot / len(sam_fac), 2)
        
    return average_tot_0 if average_tot_0 <= average_tot_180 else average_tot_180
                    

def img_res_compare(a, b):
    
    '''Image resolution compare.
    Resize(down size) the large
    image to its pair and compare'''

    # downsize 'a' to b & compare
    if a.shape[0] > b.shape[0]:
        log_it('img_res_compare(): object a is greater than b')
        a_small = im_resize(a, width=b.shape[1])
        average = image_compare(a_small, b)
        return average

    # downsize 'b' to a & compare
    elif a.shape[0] < b.shape[0]:        
        log_it('img_res_compare(): object b is greater than a')
        b_small = im_resize(b, width=a.shape[1])
        average = image_compare(a, b_small)
        return average
    else:
        return image_compare(a, b)
    

def diff_ar(a, b):

    ''' Difference array. takes 2 image
    objects & returns the difference
    average of each pixels'''    
    
    # checking resolution match & compare images
    if a.shape[:2] == b.shape[:2]:
        log_it('diff_ar(): Resolution match!')
        avg_value = image_compare(a, b)
        return avg_value
                        
    # checking aspect ratio match & compare images
    elif a_ratio(a) == a_ratio(b):
        log_it('diff_ar(): Resolution match failed. Aspect ratio match!')
        avg_value = img_res_compare(a, b)
        return avg_value

    # checking reverse aspect ratio & compare images
    elif a_ratio(a) == ra_ratio(b):
        log_it('diff_ar(): Resolution, Aspect ratio matches failed. Reverse aspect ration match!')

        # rotate second image by 90 degree clockwise & compare
        log_it('diff_ar(): Rotating 90 degree clockwise')
        b_ro90c = cv2.rotate(b, cv2.ROTATE_90_CLOCKWISE)
        avg_value_90c = img_res_compare(a, b_ro90c)

        # calculating threshold average
        th_tot = 0                                
        for p in th:
            th_tot += p                         
        th_average = round(th_tot / len(th))

        # checking if found any possilbe match
        if avg_value_90c < th_average:
            return avg_value_90c
        else:
            # rotate second image by 90 degree counter clockwise & compare
            log_it('diff_ar(): Clockwise rotated object match failed. Rotating 90 degree counter clockwise')
            b_ro90cc = cv2.rotate(b, cv2.ROTATE_90_COUNTERCLOCKWISE)
            avg_value_90cc = img_res_compare(a, b_ro90cc)
            return avg_value_90c if avg_value_90c <= avg_value_90cc else avg_value_90cc
    	
    else:
        log_it('diff_ar(): Resolution, Aspect ratio, Reverse aspect ratio match failed')
        return 250


def log_it(*logV):    
    if log_flag == True:
        lg.info(*logV)


arg_length = int(len(argv))

# Progress resume 
if arg_length > 1:
    if arg_length != 2:
        print("Insufficient or too many arguments to resume")
        print("Format: {} masterListPopulated.json".format(argv[0]))
        sys.exit("Program exit...")        
    else:        
        try:           
            print("Program started [RESUME MODE]")            
            with open(argv[1], 'r') as myList:
                m_list = json.load(myList)
            print("{} file object created".format(argv[1]))            
            p_resume = True
        except:
            sys.exit("Error reading the given arguments")
else:
    p_resume = False
    

if p_resume == False:
  
    print('Program started [NORMAL MODE]')

    '''Creating master files list'''
    m_list = [] # empty master list
    path = '.' # current directory

    spinner = sp('Collecting files ')

    # finds file names along with path & stores into a list variable
    # r = root, d = directories, f = files
    for r, d, f in os.walk(path):
        
        for file in f:            
            fl = os.path.join(r, file)
            sz = os.stat(fl).st_size
            log_it('File = %s', fl)

            if ('.jpg' in file or '.JPG' in file) and filetype.is_image(fl):
                m_list.append([fl, 'r', sz, [], 0])               
                
                # each element = ['path/fileName', 'r', <size>, <emptyList> <no walked files so far>]
                # r = ready; s = source; d = duplicate; c = ok/done/completed
                # os.stat(i).st_size # returns file(i) size
                
            spinner.next()
    spinner.finish()
    log_it('Master list created. Count = %d', len(m_list))

    with open('masterList.json', 'w') as tmp:
        json.dump(m_list, tmp)
    log_it('Master list file copied')
    log_it(' ')


'''Populating master list with search results'''
print('Processing images [Populating master list]')
ipBar = ibar('Images processed ', max=len(m_list))
down() # Start printing main progress bar one line down

for i in range(len(m_list)): # SOURCE IMAGE LOOP
    ipBar.next()

    # excluding already processed sources
    if m_list[i][1] == 'r' or m_list[i][1] == 's':    	
        
        up() # Print sub progress above main bar
        ip_sub = ibar('Current process  ', max=len(m_list) - i - 1)
        m_list[i][1] = 's' # updating m_list
        
        # creating source image object
        source_img = cv2.imread(m_list[i][0], 0)

        for j in range(i + 1, len(m_list)): # TARGET IMAGE LOOP
            
            # exclude already done comparisons                        
            if j >= m_list[i][4] and j > max([0] if not m_list[i][3] else m_list[i][3]) and m_list[j][1] != 'd' and m_list[j][1] != 's' and m_list[j][1] != 'c':
                m_list[i][4] = j
                                 
                # creating target image object
                target_img = cv2.imread(m_list[j][0], 0)
                                
                # comparing images & getting image average value
                log_it('Comparing %s & %s', m_list[i][0], m_list[j][0])
                diff_average = diff_ar(source_img, target_img)
                log_it('i = %d, j = %d, difference average = %d',i, j, diff_average)

                # calculating threshold average
                th_tot = 0                                
                for p in th:
                    th_tot += p                         
                th_average = round(th_tot / len(th))
                                
                if diff_average <= th_average:                    
                    # update m_list upon found valid image match 
                    m_list[i][3].append(j)
                    log_it('m_list[%d] appeded. Length of m_list[%d][3] = %d', i, i, len(m_list[i][3]))
                    m_list[j][1] = 'd'
                    log_it('m_list[%d][1] = %s', j, m_list[j][1])
                    
                    # update output json file whenever changes made on m_list
                    with open('masterListPopulated.json', 'w') as tmp:
                        json.dump(m_list, tmp)
                        log_it('Master list file updated.')
                        
            # update periodically
            # whlie resuming obviously program will re process 
            # the last 100 sets of images if no match was found
            if j % 100 == 0:
                with open('masterListPopulated.json', 'w') as tmp:
                    json.dump(m_list, tmp)
                    log_it('Master list file updated.')
                        
            ip_sub.next() # Prints sub process bar
        ip_sub.finish() # Clears it for next fresh run
                                                    
        m_list[i][1] = 'c'
        with open('masterListPopulated.json', 'w') as tmp:
            json.dump(m_list, tmp)
            log_it('Master list file updated.')
    
ipBar.finish() # clears the primary image processing bar

log_it('Populated Master list copied to json file for resuming. Now exporting results')
log_it(' ')

'''Generating report & savig it in a file'''
result_bar = ibar("Result generated ", max=len(m_list))

# generating results & exporting it
with open('Result.txt', 'a') as out_r:
    for i in m_list:

        # check for completed state sources & has any duplicates
        if i[1] == 'c' and len(i[3]) >= 1:
            
            # printing(exporting) the source file name
            print("{0:>10} {1}".format(i[2], i[0]), file=out_r)            

            for j in i[3]:
                # printing the duplicates along with the source
                print("{0:>10} {1}".format(m_list[j][2], m_list[j][0]), file=out_r)

            # empty line printing for differentiating next set
            print(' ', file=out_r)
        result_bar.next()
    result_bar.finish()

log_it('Done')
print('Done! Do look for the file "Result.txt"')
