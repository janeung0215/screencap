import os
import cv2
import pytesseract
from PIL import Image
import imagehash
from deepdiff import DeepDiff
from celery import Celery
celery = Celery(__name__)
celery.conf.update({
    'broker_url': 'redis://redis:6379/0',
    'result_backend': 'redis://redis:6379/0'
})

@celery.task
def capture(uploadfilename):
    frame1= -1
    path = os.getcwd()+'/static/img/'+uploadfilename+'/'
    isExist = os.path.exists(path)
    if not isExist:
        os.makedirs(path)
    currentframe = 0
    cam = cv2.VideoCapture('uploads/'+uploadfilename)
    while (True):
        ret, frame = cam.read()
        fps = int(cam.get(cv2.CAP_PROP_FPS))
        pixel =cam.get(3)*cam.get(4)
        if ret:
            if currentframe == 0:
                currentframe = currentframe+1 
                frame1 = frame
                grayframe = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
                grayframe1 = cv2.cvtColor(frame1,cv2.COLOR_BGR2GRAY)
                print(currentframe)
            elif currentframe%(3*fps) == 0:
                grayframe = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
                grayframe1 = cv2.cvtColor(frame1,cv2.COLOR_BGR2GRAY)
                print(currentframe)
                # compare 2 image
                words = []
                words2 = []
                data = 0
                data2 = 0
                change = 0
                change1= 0
                change2 = 0
                wordspixel = 0
                wordspixel2 = 0
                # get the words info using ocr 
                # how many pixels does the words consist
                #convert cv2 to PIL format
                data = pytesseract.image_to_boxes(grayframe)
                for d in data.splitlines():
                    words.append(d.split(" "))
                    for d in words:
                      wordspixel = wordspixel + (int(d[4])-int(d[2]))*(int(d[3])-int(d[1]))
                data2 = pytesseract.image_to_boxes(grayframe1)
                for d2 in data2.splitlines():
                    words2.append(d2.split(" "))
                    for d2 in words2:
                      wordspixel2 = wordspixel2 + (int(d2[4])-int(d2[2]))*(int(d2[3])-int(d2[1]))
                # if wordpixel is small then 60%  
                if wordspixel/pixel <0.5 and wordspixel2/pixel <0.5:
                # compare the pixels
                    hash0 = imagehash.phash(Image.fromarray(grayframe))
                    hash1 = imagehash.phash(Image.fromarray(grayframe1))
                    distance = hash0 - hash1
                    similarity = 1.0 - (distance / max(len(hash0.hash), len(hash1.hash)))
                    if similarity < 0.8:
                        cv2.imwrite(path+str(currentframe)+'.jpg', frame1)
                else:
                #else compare the words
                    ddiff =DeepDiff(words, words2, ignore_order=True)
                # sum the word data
                    def get_all_elements_in_list_of_lists(words):
                      count = 0
                      for element in words:
                          count += len(element)
                      return count

                    def get_all_elements_in_list_of_lists2(words2):
                      count = 0
                      for element in words2:
                          count += len(element)
                      return count

                    # calculate the change
                    if ddiff.get('values_changed')!=None:
                      x = list(ddiff.get('values_changed').values())[:]
                      for n in range(len(x)):
                          if type(list(x[n].values())[0]) == type([]):
                              for a in list(x[n].values()):
                                  change = change + len(a)
                      else:
                          change = change + len(list(x[n].values()))
                    else:
                        pass

                    if ddiff.get('iterable_item_added')!=None:
                      x1 = list(ddiff.get('iterable_item_added').values())[:]
                      for n1 in x1:
                          if type(n1) == type([]):
                              change1 = change1 + len(n1)
                          else:
                              change1 = change1 + 1
                    else:
                      pass
                    if ddiff.get('iterable_item_removed')!=None:
                      x2 = list(ddiff.get('iterable_item_removed').values())[:]
                      for n2 in x2:
                          if type(n2) == type([]):
                              change2 = change2 + len(n2)
                          else:
                              change2 = change2 + 1
                    else:
                      pass
                    #calculate the simularity
                    similarity = 1-((change + change1 + change2)/(get_all_elements_in_list_of_lists(words)+get_all_elements_in_list_of_lists2(words2)))
                    print(similarity)
                  #upload if simluarity is smaller than 60% 
                    if similarity < 0.95:
                        cv2.imwrite(path+str(currentframe)+'.jpg', frame1)
                currentframe = currentframe+1                 
                frame1 = frame
            else:
                currentframe=currentframe+1
                frame1 = frame
                grayframe = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
                grayframe1 = cv2.cvtColor(frame1,cv2.COLOR_BGR2GRAY)
                print(currentframe)

        if ret == False:
            break
    cam.release()
    return fps
