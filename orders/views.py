from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from carts.models import CartItem
from .forms import OrderForm
import datetime
from .models import Order, Payment, OrderProduct
import json
from store.models import Product
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

# SSLCommerz
from django.conf import settings
from sslcommerz_lib import SSLCOMMERZ
from django.views.decorators.csrf import csrf_exempt
import uuid


def process_order(order, payment=None):
    cart_items = CartItem.objects.filter(user=order.user)
    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order_id = order.id
        orderproduct.payment = payment
        orderproduct.user_id = order.user.id
        orderproduct.product_id = item.product_id
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        orderproduct = OrderProduct.objects.get(id=orderproduct.id)
        orderproduct.variations.set(product_variation)
        orderproduct.save()

        # Reduce the quantity of the sold products
        product = Product.objects.get(id=item.product_id)
        product.stock -= item.quantity
        product.save()

    # Clear cart
    CartItem.objects.filter(user=order.user).delete()

    


@csrf_exempt
def payments(request, order_number):
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=order_number)
    if order.payment_method == "Cash on Delivery":
        order.is_ordered = True
        order.save()
        process_order(order)
        return redirect(reverse('order_complete', kwargs={'order_number': order_number, 'tran_id': 'cash_on_delivery'}))

    elif order.payment_method == "Bkash":
        sslcommerz_settings = {
            'store_id': settings.STORE_ID,
            'store_pass': settings.STORE_PASSWORD,
            'issandbox': settings.IS_SANDBOX,
        }

        sslcommez = SSLCOMMERZ(sslcommerz_settings)

        order_status_url = request.build_absolute_uri(reverse('order_status', kwargs={'order_number': order_number}))
        post_body = {
            'total_amount': str(order.order_total),  # Ensure the amount is in string format
            'currency': "BDT",
            'tran_id': str(uuid.uuid4()),  # Use uuid to generate  the unique transaction ID
            'success_url': order_status_url,
            'fail_url': order_status_url,
            'cancel_url': request.build_absolute_uri('/payment-cancelled/'),
            'emi_option': 0,
            'cus_name': order.full_name,
            'cus_email': order.email,
            'cus_phone': order.phone,
            'cus_add1': order.address_line_1,
            'cus_city': order.city,
            'cus_country': order.country,
            'shipping_method': "NO",
            'multi_card_name': "",
            'num_of_item': "",
            'product_name': "Order #{}".format(order_number),
            'product_category': "General",
            'product_profile': "general"
        }


        
        response = sslcommez.createSession(post_body)
        if response['status'] == 'SUCCESS':
            return redirect(response['GatewayPageURL'])
                


def place_order(request, total=0, quantity=0,):
    current_user = request.user

    # If the cart count is less than or equal to 0, then redirect back to shop
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2 * total)/100
    grand_total = total + tax


    PAYMENT_METHOD = {
        'cash_on_delivery': 'Cash on Delivery',
        'bkash': 'Bkash',
    }


    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Store all the billing information inside Order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')

            # Payment Method getting the value from key
            payment_method_key = form.cleaned_data['payment_method']
            data.payment_method = PAYMENT_METHOD[payment_method_key] 

            data.save()
            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d") #20210305
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }
            return render(request, 'orders/payments.html', context)
    else:
        return redirect('checkout')



@csrf_exempt
def order_status(request, order_number):
    if request.method == "POST":
        body = request.POST
        print(body['status'])

        try:
            order = Order.objects.get(order_number=order_number, is_ordered=False)

            if body['status'] == 'VALID':
                payment = Payment(
                    user=order.user,
                    payment_id=body.get('tran_id'),
                    payment_method="Bkash",
                    amount_paid=order.order_total,
                    status=body.get('status'),
                )
                payment.save()

                order.payment = payment
                order.is_ordered = True
                order.save()
                
                process_order(order, payment)

                return redirect(reverse('order_complete', kwargs={'order_number': order_number, 'tran_id': body.get('tran_id')}))

            elif body['status'] == 'FAILED':
                return render(request, 'orders/payment_failed.html')

        except Order.DoesNotExist:
            return HttpResponse('Order does not exist')

    return HttpResponse('Invalid request')




@csrf_exempt
def order_complete(request, order_number, tran_id):
    
    order = Order.objects.get(order_number=order_number, is_ordered=True)
    ordered_products = OrderProduct.objects.filter(order_id=order.id)

    subtotal = 0
    for i in ordered_products:
        subtotal += i.product_price * i.quantity
    
    if tran_id != 'cash_on_delivery':
        payment = Payment.objects.get(payment_id=tran_id)
        payment_id = payment.payment_id
        status = payment.status
    else:
        payment = 'On delivery'
        payment_id = None
        status = 'Pending'

    # Send order received email to customer
    mail_subject = 'Thank you for ordering from KenaKata!'
    message = render_to_string('orders/order_recieved_email.html', {
        'user': order.user,
        'order': order,
        'ordered_products': ordered_products,
        'order_number': order_number,
        'transID': payment_id,
        'payment': payment,
        'subtotal': subtotal,
        'status': status,
    })
    to_email = order.user.email
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()



    context = {
        'order': order,
        'ordered_products': ordered_products,
        'order_number': order.order_number,
        'transID': payment_id,
        'payment': payment,
        'subtotal': subtotal,
        'status': status,
    }
    return render(request, 'orders/order_complete.html', context)
    # except (Payment.DoesNotExist, Order.DoesNotExist):
    #     return HttpResponse('Order was not completed')