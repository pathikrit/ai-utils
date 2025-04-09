from dotenv import load_dotenv
load_dotenv()

from nova_act import NovaAct

from pydantic import BaseModel

class PaymentMethods(BaseModel):
    providers: list[str]


with NovaAct(starting_page="https://littlekorboose.com/") as nova:
    nova.act("go to the product directory")
    nova.act("drill down to a product that we can buy on this site")
    nova.act("add to cart")
    nova.act("go to checkout - go to the final page where I can enter payment info")
    prompt = " ".join([
        "What are all the digital payment solutions options?",
        "I am not interested in networks like Visa or Amex",
        "but digital wallets or payment gateways like Stripe or Amazon Pay etc."
    ])

    providers = nova.act(prompt, schema=PaymentMethods.model_json_schema())
    print(providers)
