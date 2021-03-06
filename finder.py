import boto3
import bs4 as bs
import requests
import shelve

sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('apartment-finder')


domain = "http://www.bexleylakeline.com/"
url = "availableunits.aspx?control=1&myolePropertyID=535202"
desired_floorplans = {
    "2142865":"The Bluebonnet",
    "2258460":"The Lonestar with Fenced-In Yard",
    "2258459":"The Longhorn with Fenced-In Yard",
    "2283633":"The Longhorn with Garage and Fenced Yard",
}
result_dict = {}

def load_website(floorplan,domain=domain,url=url):
    temp = []
    r = requests.get(domain + url)
    soup = bs.BeautifulSoup(r.text, 'html.parser')
    soup.thead.decompose()
    try:
        divid = 'divFPH_'+str(floorplan)
        table = soup.find("table", {"id": divid})
        table = table.find_all("td")
        for cell in table:
            cell = cell.get_text().splitlines()
            cell = [x.strip() for x in cell if x.strip()]
            temp.append(cell)
        return temp
    except:
        return False

for floorplan in desired_floorplans.keys():
    current = ''
    result_set = load_website(floorplan)
    if result_set != False:
        for item in result_set:
            try:
                if item[0][0] == '#':
                    result_dict[item[0]] = []
                    current = item[0]
                    result_dict[current].append(floorplan)
                else:
                    result_dict[current].append(item)
            except:
                pass

for key in result_dict.keys():
    msg = "Listed: "+key+"-"+desired_floorplans[result_dict[key][0]]+"-"+'-'.join(result_dict[key][3][1:])+"-"+''.join(result_dict[key][4])
    apt_list =  table.get_item(
                    Key={
                        "key":"apt"
                    }
                )
    if "Item" not in apt_list:
        nlist = [key]
        table.put_item(
            Item={
                'key': 'apt',
                'entry': nlist
            }
        )
        sns.publish(TopicArn="arn:aws:sns:us-east-1:905998010507:apartment-notification",Message=msg)
    else:
        item = apt_list['Item']['entry']
        if key not in item:
            item = apt_list['Item']['entry']
            item.append(key)
            print(item)
            table.update_item(
                Key={
                    'key': 'apt'
                },
                UpdateExpression='SET entry = :nentry',
                ExpressionAttributeValues={
                    ':nentry': item
                }
            )
            sns.publish(TopicArn="arn:aws:sns:us-east-1:905998010507:apartment-notification",Message=msg)
    apt_entry = table.get_item(
                    Key={
                        "key":key
                    }
                )
    if "Item" not in apt_entry:
        table.put_item(
            Item={
                'key': key,
                'entry': result_dict[key],
            }
        )

apt_list =  table.get_item(
                Key={
                    "key":"apt"
                }
            )
for apt in apt_list["Item"]["entry"]:
    apt_entry = table.get_item(
                    Key={
                        "key":apt
                    }
                )
    msg = "Delisted: "+apt+"-"+desired_floorplans[apt_entry["Item"]["entry"][0]]+"-"+'-'.join(apt_entry["Item"]["entry"][3][1:])+"-"+'-'.join(apt_entry["Item"]["entry"][4])
    if result_dict.get(apt) == None:
        response = table.delete_item(
            Key={
                "key":apt
            }
        ) 
        sns.publish(TopicArn="arn:aws:sns:us-east-1:905998010507:apartment-notification",Message=msg)
