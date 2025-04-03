from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.views.generic import ListView, DetailView
from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .forms import ProductForm, CartItemForm, CheckoutForm
from .forms import CustomUserCreationForm


# Producer Dashboard View
@login_required
def producer_dashboard(request):
    if request.user.role != 'producer':
        return redirect('product_list')

    products = Product.objects.filter(producer=request.user)
    return render(request, 'products/producer_dashboard.html', {'products': products})


# Add Product View
@login_required
def add_product(request):
    if request.user.role != 'producer':
        return redirect('product_list')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = request.user
            product.save()
            return redirect('producer_dashboard')

    else:
        form = ProductForm()
    return render(request, 'products/add_product.html', {'form': form})


# Home View
def home(request):
    categories = Category.objects.all()
    featured_products = Product.objects.filter(available=True).order_by('-created_at')[:8]
    context = {
        'categories': categories,
        'featured_products': featured_products,
    }
    return render(request, 'store/home.html', context)


# User Registration View
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('home')
        else:
            messages.error(request, "Registration failed. Please try again.")
    else:
        form = CustomUserCreationForm(request.POST)


    return render(request, 'registration/register.html', {'form': form})


# Product List View with Search and Category Filter
class ProductListView(ListView):
    model = Product
    template_name = 'store/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset().filter(available=True)
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['category_slug'] = self.kwargs.get('category_slug')
        context['search_query'] = self.request.GET.get('search', '')
        return context


# Product Detail View
class ProductDetailView(DetailView):
    model = Product
    template_name = 'store/product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_products'] = Product.objects.filter(
            category=self.object.category
        ).exclude(id=self.object.id)[:4]
        return context


# Add to Cart View
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f"{product.name} added to your cart.")
    return redirect('cart_detail')


# Remove from Cart View
@login_required
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from your cart.")
    return redirect('cart_detail')


# Update Cart Item View
@login_required
def update_cart_item(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
    if request.method == 'POST':
        form = CartItemForm(request.POST, instance=cart_item)
        if form.is_valid():
            form.save()
            messages.success(request, "Cart updated.")
            return redirect('cart_detail')
    else:
        form = CartItemForm(instance=cart_item)
    return render(request, 'store/update_cart_item.html', {'form': form})


# Cart Detail View
@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/cart_detail.html', {'cart': cart})


# Checkout View
@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    if cart.items.count() == 0:
        messages.warning(request, "Your cart is empty.")
        return redirect('product_list')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.total = cart.total
            order.save()

            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price=item.product.price,
                    quantity=item.quantity
                )

            cart.items.all().delete()
            messages.success(request, "Your order has been placed successfully!")
            return redirect('order_detail', pk=order.pk)
    else:
        initial_data = {
            'address': request.user.address,
            'payment_method': 'credit_card',
            'delivery_date': timezone.now() + timezone.timedelta(days=2)
        }
        form = CheckoutForm(initial=initial_data)

    return render(request, 'store/checkout.html', {
        'form': form,
        'cart': cart
    })


# Order List View
@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_list.html', {'orders': orders})


# Order Detail View
@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'store/order_detail.html', {'order': order})
