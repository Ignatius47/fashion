from django.views.generic import TemplateView, ListView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Product, Category, Collection, Cart, Order, BlogPost, Brand, Tag, PriceRange, Size, Color, User
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from .serializers import ProductSerializer, CategorySerializer, CartSerializer, OrderSerializer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import CartItem
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


class HomeView(TemplateView):
    """Renders the homepage with featured collections and latest products."""
    template_name = 'shop/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_collection'] = Collection.objects.filter(is_featured=True).first()
        context['latest_products'] = Product.objects.filter(is_available=True).order_by('-created_at')[:8]
        return context

class ShopView(ListView):
    model = Product
    template_name = 'shop/shop.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_available=True)

        # Filter by category
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Filter by brand
        brand_slug = self.request.GET.get('brand')
        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)

        # Filter by size
        size_slug = self.request.GET.get('size')
        if size_slug:
            queryset = queryset.filter(sizes__slug=size_slug)

        # Price range filtering
        price_ranges = {
            "0-500": (0, 500),
            "501-1000": (501, 1000),
            "1001-5000": (1001, 5000),
            "5001-999999": (5001, None),
        }

        price_range_key = self.request.GET.get('price')
        if price_range_key in price_ranges:
            min_price, max_price = price_ranges[price_range_key]
            if max_price:
                queryset = queryset.filter(price__gte=min_price, price__lte=max_price)
            else:
                queryset = queryset.filter(price__gte=min_price)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Price ranges to display in the template
        context["price_ranges"] = [
            {"label": "Under Ksh 500", "value": "0-500"},
            {"label": "Ksh 501 - 1000", "value": "501-1000"},
            {"label": "Ksh 1001 - 5000", "value": "1001-5000"},
            {"label": "Above Ksh 5000", "value": "5001-999999"},
        ]

        # Selected filter values
        context["selected_price"] = self.request.GET.get("price")
        context["selected_category"] = self.request.GET.get("category")
        context["selected_brand"] = self.request.GET.get("brand")
        context["selected_size"] = self.request.GET.get("size")

        return context


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['brands'] = Brand.objects.all()
        context['price_ranges'] = PriceRange.objects.all()
        context['sizes'] = Size.objects.all()
        context['colors'] = Color.objects.all()
        context['tags'] = Tag.objects.all()
        return context


def add_to_cart(request, slug):
    print(f"Request method: {request.method}")
    print(f"Slug received: {slug}")
    
    # Fetch the product or return 404 if not found
    product = get_object_or_404(Product, slug=slug)

    # Retrieve session cart (default to empty dictionary)
    cart = request.session.get('cart', {})

    # Update cart logic
    if slug in cart:
        cart[slug]['quantity'] += 1
    else:
        cart[slug] = {
            'name': product.name,
            'price': str(product.price),  # Convert Decimal to string for session storage
            'quantity': 1,
            'image': product.image.url if hasattr(product, 'image') and product.image else None
        }

    # Save updated cart in session
    request.session['cart'] = cart
    request.session.modified = True  # Ensure session updates

    return redirect('shopping-cart')


# @login_required
def remove_from_cart(request, product_id):
    cart_item = get_object_or_404(CartItem, cart__user=request.user, product_id=product_id)
    cart_item.delete()
    return redirect('shopping-cart')



class ProductDetailView(DetailView):
    """Displays the details of a single product."""
    model = Product
    template_name = 'shop/shop-details.html'
    context_object_name = 'product'
    slug_url_kwarg = 'product_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_products'] = Product.objects.filter(
            category=self.object.category
        ).exclude(id=self.object.id)[:4]
        return context

class CartView(TemplateView):
    """Renders the shopping cart page."""
    template_name = 'shop/shopping-cart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the cart from session (default to an empty dict if not set)
        cart = self.request.session.get('cart', {})

        # Convert cart items into a list for the template
        cart_items = []
        cart_total = 0

        for slug, item in cart.items():
            total_price = float(item['price']) * item['quantity']
            cart_items.append({
                'slug': slug,
                'name': item['name'],
                'price': item['price'],
                'quantity': item['quantity'],
                'image': item['image'],
                'total_price': total_price,
            })
            cart_total += total_price

        context['cart_items'] = cart_items
        context['cart_total'] = cart_total
        return context


class CheckoutView(LoginRequiredMixin, TemplateView):
    """Handles checkout process and displays user’s cart items."""
    template_name = 'shop/checkout.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        context['cart_items'] = cart.items.all()
        context['shipping_addresses'] = self.request.user.addresses.all()
        return context

class BlogView(ListView):
    """Renders the blog list page."""
    template_name = 'shop/blog.html'
    model = BlogPost
    context_object_name = 'posts'
    paginate_by = 6


class BlogDetailView(DetailView):
    """Renders a single blog post."""
    template_name = 'shop/blog-details.html'
    model = BlogPost
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_posts'] = BlogPost.objects.exclude(id=self.object.id).order_by('-created_at')[:3]
        return context

    def get_object(self):
        return get_object_or_404(BlogPost, pk=self.kwargs['pk'])
    
class AboutView(TemplateView):
    template_name = "shop/about.html"

class ShopDetailView(DetailView):
    model = Product
    template_name = "shop/shop_details.html"
    context_object_name = "product"

    def get_object(self):
        return get_object_or_404(Product, slug=self.kwargs['product_slug'])
    


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """ API view for retrieving product details. """
    queryset = Product.objects.filter(is_available=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ API view for retrieving categories. """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class CartViewSet(viewsets.ModelViewSet):
    """ API view for managing shopping cart. """
    serializer_class = CartSerializer
    queryset = Cart.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

class OrderViewSet(viewsets.ModelViewSet):
    """ API view for managing orders. """
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)



@csrf_exempt
def add_to_cart(request):
    if request.method == "POST":
        data = json.loads(request.body)
        product_id = data.get("product_id")

        if not request.user.is_authenticated:
            return JsonResponse({"success": False, "error": "User not logged in"})

        product = Product.objects.get(id=product_id)
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart.items.add(product)  # Assuming ManyToMany relationship with Product

        cart_count = cart.items.count()

        return JsonResponse({"success": True, "cart_count": cart_count})
    
    return JsonResponse({"success": False})


@csrf_exempt
def remove_from_cart(request, product_id):
    if request.method == 'POST':
        # Logic to remove the item from the cart
        # For example, you might remove the item from the session or database
        cart = request.session.get('cart', {})
        if str(product_id) in cart:
            del cart[str(product_id)]
            request.session['cart'] = cart
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Item not found in cart.'})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


    
class AboutView(TemplateView):
    template_name = "shop/about.html"

class ShopDetailsView(TemplateView):
    template_name = "shop/shop-details.html"

class ShoppingCartView(TemplateView):
    template_name = "shop/shopping-cart.html"

class CheckoutView(TemplateView):
    template_name = "shop/checkout.html"

class BlogDetailsView(TemplateView):
    template_name = "shop/blog-details.html"

class ContactView(TemplateView):
    template_name = "shop/contact.html"





def update_cart(request):
    """Update cart item quantity."""
    if request.method == "POST":
        cart_item_id = request.POST.get("cart_item_id")
        new_quantity = int(request.POST.get("quantity"))

        cart_item = get_object_or_404(CartItem, id=cart_item_id)
        cart_item.quantity = new_quantity
        cart_item.save()

        return JsonResponse({"success": True, "new_total": cart_item.get_total_price()})


def remove_from_cart(request):
    """Remove item from cart."""
    if request.method == "POST":
        cart_item_id = request.POST.get("cart_item_id")
        cart_item = get_object_or_404(CartItem, id=cart_item_id)
        cart_item.delete()

        return JsonResponse({"success": True})
