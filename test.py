from datetime import datetime

abc = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

abc.append(11)

for i in range(1, len(abc)):
    print(abc[i])

date_str = "10/09/2024"
date = datetime.strptime(date_str, "%d/%m/%Y")
print(date)
formatted_date = date.strftime("%B of %Y")
print(formatted_date)