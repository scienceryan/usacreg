import datetime

def main():

    family = [
        {"name" : "Ryan", "role" : "dad", "birthdate" : datetime.datetime(1972, 7, 2)},
        {"name" : "Suz", "role" : "mom", "birthdate" : datetime.datetime(1974, 12, 18)},
        {"name" : "Seneca", "role" : "daugther", "birthdate" : datetime.datetime(2006, 6, 30)},
        {"name" : "Max", "role" : "son", "birthdate" : datetime.datetime(2008, 8, 8)}
    ]

    for person in family:
        print(person["name"], person["birthdate"].strftime("%m/%d/%Y"))

    while True:
        try:
            income = float(input("What is your taxable ordinary income? "))
            print(f"You entered an income of ${income:0,.0f}")
            if income >= 0.0:
                tax_fed = tax(income)
                tax_ca = tax(income,"CA")
                tax_tot = tax_fed + tax_ca
                print(f"Federal taxes = ${tax_fed:0,.0f}" )
                print(f"California taxes = ${tax_ca:0,.0f}" )
                print(f"TOTAL TAX = ${tax_tot:0,.0f}")

        except ValueError:
            print("You did not enter a valid number.")
        else:
            break



def tax(income,state="FED"):
    taxbrackets = { "FED":((731201.00, 0.37),
                      (487451.00, 0.35),
                      (383901.00, 0.32),
                      (201051.00, 0.24),
                      (94301.00, 0.22),
                      (23201.00, 0.12),
                      (1.0, 0.10)),
                "CA": ((1396542.00, 0.123),
                      (837922.00, 0.113),
                      (698274.00, 0.103),
                      (136700.00, 0.093),
                      (108162.00, 0.080),
                      (77918.00, 0.060),
                      (49368.00, 0.040),
                       (20824.00, 0.20),
                        (1.0, 0.10))}
    tax = 0.0
    taxbracket = taxbrackets[state]
    print(state)

    for bracket in taxbracket:
        bracketincome = income - bracket[0] + 1.0
        if bracketincome > 0.0:
            marginaltax = bracketincome * bracket[1]
            print(f"{bracket[1]*100.00}% tax bracket| income = ${bracketincome:0,.0f} | tax = ${marginaltax:0,.0f}")
            tax += marginaltax
            income = bracket[0] - 1.0
        
    return tax


main()
